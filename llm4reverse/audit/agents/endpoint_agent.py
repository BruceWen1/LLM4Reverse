# -*- coding: utf-8 -*-
"""
endpoint_agent.py
Audit Module - Agents
=====================

This module enriches static endpoint findings by orchestrating a LangGraph
ReAct agent with two custom tools—SymbolLookupTool and CodeSearchTool.  
The agent analyses each finding, infers missing request metadata
(headers/parameters/payload schema), and returns a single-line JSON summary.

All OpenAI traffic is routed through `llm.client.get_chat_llm`, allowing easy
backend replacement (e.g. corporate API gateway).
"""

from __future__ import annotations

import json
import logging
from typing import Dict, List, Optional, Tuple

from langchain_core.prompts import PromptTemplate
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from llm4reverse.audit.extractors.regex_extractor import Finding
from llm4reverse.audit.resolvers.symbol_index import SymbolIndex
from llm4reverse.llm.client import get_chat_llm
from llm4reverse.audit.tools.symbol_lookup import _make_symbol_lookup_tool
from llm4reverse.audit.tools.code_search import _make_code_search_tool

# Try to import LangChain agents - prefer create_react_agent (0.3.x recommended)
try:
    from langchain.agents import create_react_agent, AgentExecutor
    HAS_CREATE_REACT_AGENT = True
except ImportError:
    HAS_CREATE_REACT_AGENT = False

try:
    from langchain.agents import AgentType, initialize_agent
    HAS_INITIALIZE_AGENT = True
except ImportError:
    HAS_INITIALIZE_AGENT = False

logger = logging.getLogger(__name__)


# Define a custom ReAct JSON prompt compatible with LangChain 0.3.27
CustomReActPrompt = PromptTemplate.from_template(
    """You are a security engineer analysing JavaScript frontend code.
You may call tools to gather additional information.

Available tools:
{tools}

Tool names:
{tool_names}

Use the following format for reasoning:
Thought: describe your thought
Action: one of [{tool_names}]
Action Input: the input for the action
Observation: the result of the action
… (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer

For the following endpoint, describe:
- Missing URL parts (e.g. baseURL variables)
- Required headers or auth tokens
- Body/query parameters with types

Return the final answer as a single-line JSON with keys:
`url`, `method`, `headers`, `params`, `body`, `confidence`.

Question: {input}
{agent_scratchpad}"""
)


class TraceCallback(BaseCallbackHandler):
    """
    TraceCallback

    Collects every assistant message for later inspection/report generation.
    """

    def __init__(self) -> None:
        """Initialize an empty list to store LLM events."""
        self.events: List[Dict[str, str]] = []

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Skip token-level logging to avoid excessive trace size."""
        pass

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        """
        Append the final assistant message of each LLM call to events.

        Args:
            response (LLMResult): The LLMResult containing the generations.
        """
        self.events.append({
            "role": "assistant",
            "content": response.generations[0][0].text
        })


def run_trace(
    findings: List[Finding],
    index: SymbolIndex,
    model_name: Optional[str],
) -> Tuple[List[Finding], List[Dict[str, str]]]:
    """
    Enrich every Finding via a LangGraph ReAct agent.

    Args:
        findings (List[Finding]): List of raw endpoint findings.
        index (SymbolIndex): Prebuilt symbol index for variable resolution.
        model_name (Optional[str]): Name of the OpenAI model to use; falls back to .env default.

    Returns:
        Tuple[List[Finding], List[Dict[str, str]]]:
            - enriched findings with added metadata
            - ordered trace of all assistant messages
    """
    logger.info("Starting LLM enrichment (model=%s)", model_name or "[env default]")

    # Instantiate the ChatOpenAI client
    llm = get_chat_llm(model_name=model_name, temperature=0.0)

    # Prepare custom tools for the agent
    tools = [
        _make_symbol_lookup_tool(index),
        _make_code_search_tool(index),
    ]

    # Attach trace callback to collect assistant outputs
    tracer = TraceCallback()
    try:
        from langchain_core.callbacks import CallbackManager
        cb_manager = CallbackManager([tracer])
        logger.debug("CallbackManager initialized.")
    except Exception as exc:
        logger.warning("Could not create CallbackManager – %s", exc)
        cb_manager = None

    # Build agent: prefer create_react_agent with AgentExecutor (0.3.x recommended)
    # Fallback to legacy initialize_agent if needed
    agent_executor = None
    use_legacy_agent = False
    
    if HAS_CREATE_REACT_AGENT:
        try:
            # Primary: use create_react_agent with AgentExecutor (recommended for 0.3.x)
            agent = create_react_agent(llm=llm, tools=tools, prompt=CustomReActPrompt)
            agent_executor = AgentExecutor(
                agent=agent, 
                tools=tools, 
                verbose=False, 
                handle_parsing_errors=True
            )
            use_legacy_agent = False
            logger.debug("Using create_react_agent with AgentExecutor (primary).")
        except Exception as exc_create:
            logger.warning("create_react_agent failed: %s, trying fallback", exc_create)
            if HAS_INITIALIZE_AGENT:
                try:
                    # Fallback: use legacy initialize_agent
                    agent_executor = initialize_agent(
                        tools=tools,
                        llm=llm,
                        agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                        verbose=False,
                        handle_parsing_errors=True,
                    )
                    use_legacy_agent = True
                    logger.debug("Using initialize_agent (fallback).")
                except Exception as exc_init:
                    logger.error("Both agent creation methods failed. create_err=%s init_err=%s", exc_create, exc_init)
                    raise
            else:
                logger.error("create_react_agent failed and initialize_agent not available: %s", exc_create)
                raise
    elif HAS_INITIALIZE_AGENT:
        try:
            # Only fallback available
            agent_executor = initialize_agent(
                tools=tools,
                llm=llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=False,
                handle_parsing_errors=True,
            )
            use_legacy_agent = True
            logger.debug("Using initialize_agent (only option available).")
        except Exception as exc_init:
            logger.error("initialize_agent failed: %s", exc_init)
            raise
    else:
        raise ImportError("Neither create_react_agent nor initialize_agent are available. Please check LangChain installation.")

    enriched: List[Finding] = []

    # Iterate through each finding and invoke the agent
    for f in findings:
        # Construct the user message including file context and snippet
        user_msg = (
            f"File: {f.file}:{f.line}\n"
            f"Code:\n{f.snippet}\n"
            "Think step-by-step. Use tools when needed."
        )

        logger.info("Enriching %s:%d", f.file, f.line)
        try:
            # Invoke the agent with proper configuration
            raw = None
            if use_legacy_agent:
                # Legacy initialize_agent uses .run() method
                raw = agent_executor.run(user_msg)
            else:
                # AgentExecutor path - use invoke
                raw = agent_executor.invoke({"input": user_msg})

            # Extract the JSON string from agent output
            if isinstance(raw, dict):
                result_text = raw.get("output", "")
                # Also check for intermediate_steps or other keys
                if not result_text and "intermediate_steps" in raw:
                    logger.debug("Found intermediate_steps in response: %s", raw.get("intermediate_steps", []))
                if not result_text:
                    result_text = raw.get("answer", raw.get("result", str(raw)))
            else:
                result_text = str(raw)

            result_text = result_text.strip()
            logger.debug("Agent output (len=%d): %s", len(result_text), result_text[:200] if result_text else "empty")

            # Parse JSON or fallback to raw text
            try:
                parsed = json.loads(result_text)
            except json.JSONDecodeError:
                logger.warning(
                    "Non-JSON output for %s:%d; storing raw text.", f.file, f.line
                )
                parsed = {"raw": result_text}

            # Update the finding with enriched metadata
            if isinstance(parsed, dict):
                f.url = parsed.get("url", f.url)
                f.method = parsed.get("method", f.method)
                f.snippet += f"\n/* LLM Enrich: {json.dumps(parsed, ensure_ascii=False)} */"
                f.confidence = parsed.get("confidence", f.confidence or 0.9)
            else:
                f.snippet += f"\n/* LLM Raw: {result_text} */"

            enriched.append(f)

        except Exception as exc:
            # Log and preserve the original finding on failure
            import traceback
            import sys
            error_type = type(exc).__name__
            error_msg = str(exc) if exc else "Unknown error"
            exc_info = sys.exc_info()
            full_traceback = "".join(traceback.format_exception(*exc_info))
            logger.warning(
                "Enrichment failed on %s:%d – %s: %s", 
                f.file, f.line, error_type, error_msg
            )
            # Print full traceback to stderr for debugging (in addition to logging)
            print(f"ERROR in {f.file}:{f.line} - {error_type}: {error_msg}", file=sys.stderr)
            print(full_traceback, file=sys.stderr)
            enriched.append(f)

    # Extract the collected trace events
    trace_events = tracer.events
    logger.info("Completed enrichment for %d findings", len(enriched))
    return enriched, trace_events


def _quick_test() -> None:
    """Simple import test to verify module loads without errors."""
    logger.info("endpoint_agent module loaded successfully.")


if __name__ == "__main__":
    # Configure basic logging and run self-test
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    _quick_test()


