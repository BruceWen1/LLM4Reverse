# -*- coding: utf-8 -*-
"""
har_agent.py
Reverse Module - Agents
=====================

LangChain ReAct agent that inspects HAR content and infers REST/GraphQL
interfaces.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Dict, List, Tuple, Optional, Any

from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from llm4reverse.llm.client import get_chat_llm

# Using LangChain 0.3.x agent API
from langchain.agents import create_react_agent, AgentExecutor

logger = logging.getLogger(__name__)


def _make_har_search_tool(har_dict: Dict) -> Tool:
    """
    Create a LangChain Tool that searches HAR entries by substring.
    """
    entries = har_dict["log"]["entries"]

    def _search(query: str) -> str:
        matches = []
        for e in entries:
            if query.lower() in e["request"]["url"].lower():
                matches.append(
                    {
                        "url": e["request"]["url"],
                        "method": e["request"]["method"],
                        "status": e["response"]["status"],
                        "req_headers": e["request"]["headers"][:3],
                        "res_headers": e["response"]["headers"][:3],
                    }
                )
            if len(matches) >= 10:
                break
        return json.dumps(matches, ensure_ascii=False)

    return Tool(
        name="HarSearch",
        description=(
            "Search HTTP requests in the HAR file. "
            "Input: any substring to match the request URL or headers. "
            "Output: up to 10 matching entries (JSON string)."
        ),
        func=_search,
    )


class TraceCallback(BaseCallbackHandler):
    """
    Trace callback handler for LangChain agents.
    
    Collects all assistant responses for later inspection.
    This class acts as a LangChain callback handler, recording each LLM output.
    """

    def __init__(self) -> None:
        """
        Initialize trace callback, creating an empty event list.
        """
        self.events: List[Dict] = []
        self.step_count = 0  # Step counter for progress tracking

    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs) -> None:
        """
        Called when LLM starts generating, outputs progress information.
        
        Args:
            serialized (Dict[str, Any]): Serialized LLM configuration.
            prompts (List[str]): List of input prompts.
            **kwargs: Additional keyword arguments.
        """
        self.step_count += 1
        logger.info("LLM call #%d: Starting...", self.step_count)

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:  # noqa: D401
        """
        Called when LLM finishes generating, records response content.
        
        Args:
            response (LLMResult): LLM response result.
            **kwargs: Additional keyword arguments.
        """
        try:
            logger.info("LLM call #%d: Completed", self.step_count)
            # Extract generated text content
            if response.generations and len(response.generations) > 0:
                if response.generations[0] and len(response.generations[0]) > 0:
                    text = response.generations[0][0].text
                    self.events.append({"role": "assistant", "content": text})
                    logger.debug("Recorded LLM output: %s", text[:100] if len(text) > 100 else text)
        except Exception as e:
            logger.warning("Failed to record LLM output: %s", e)

    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs) -> None:
        """
        Called when tool call starts, outputs progress information.
        
        Args:
            serialized (Dict[str, Any]): Serialized tool configuration.
            input_str (str): Tool input string.
            **kwargs: Additional keyword arguments.
        """
        tool_name = serialized.get("name", "unknown")
        logger.info("Tool call: %s (input: %s...)", tool_name, input_str[:50] if len(input_str) > 50 else input_str)

    def on_tool_end(self, output: str, **kwargs) -> None:
        """
        Called when tool call ends, outputs progress information.
        
        Args:
            output (str): Tool output string.
            **kwargs: Additional keyword arguments.
        """
        logger.info("Tool call completed (output length: %d)", len(output) if output else 0)


def _extract_json_from_text(text: str) -> Optional[List[Dict]]:
    """
    Extract JSON array from text.
    
    Agent responses may contain additional text. This function attempts to extract
    a pure JSON array from the response.
    
    Args:
        text (str): Text that may contain JSON.
        
    Returns:
        Optional[List[Dict]]: Extracted JSON array, or None if extraction fails.
    """
    if not text:
        return None
    
    # First attempt to parse the entire text directly
    try:
        parsed = json.loads(text.strip())
        if isinstance(parsed, list):
            return parsed
    except json.JSONDecodeError:
        pass
    
    # Try to find JSON array using regex
    # Match content from [ to ]
    json_pattern = r'\[[\s\S]*?\]'
    matches = re.findall(json_pattern, text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                logger.debug("Successfully extracted JSON array from text")
                return parsed
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON in code blocks
    code_block_pattern = r'```(?:json)?\s*(\[[\s\S]*?\])\s*```'
    matches = re.findall(code_block_pattern, text, re.MULTILINE | re.DOTALL)
    
    for match in matches:
        try:
            parsed = json.loads(match)
            if isinstance(parsed, list):
                logger.debug("Successfully extracted JSON array from code block")
                return parsed
        except json.JSONDecodeError:
            continue
    
    logger.warning("Failed to extract JSON array from text: %s", text[:200])
    return None


def run_har_agent(har_dict: Dict) -> Tuple[List[Dict], List[Dict]]:
    """
    Run ReAct agent on HAR dictionary to extract API endpoint information.
    
    Args:
        har_dict (Dict): HAR content (Python object).
        
    Returns:
        Tuple[List[Dict], List[Dict]]: Parsed endpoint list and raw trace logs.
    """
    logger.info("Starting HAR agent analysis")
    
    # Initialize LLM and tools
    logger.info("Initializing LLM client...")
    llm = get_chat_llm(temperature=0)
    logger.info("LLM client initialized")
    
    logger.info("Creating HAR search tool...")
    tools = [_make_har_search_tool(har_dict)]
    logger.info("Tool created")
    
    tracer = TraceCallback()
    
    # Count HAR entries
    num_entries = len(har_dict.get("log", {}).get("entries", []))
    logger.info("HAR contains %d entries", num_entries)

    # Build ReAct prompt using PromptTemplate
    react_prompt = PromptTemplate.from_template(
        """You are analysing a HAR dump.
You may call tools to gather additional information.

Available tools:
{tools}

Tool names:
{tool_names}

Use the following format:
Thought: describe your thought
Action: one of [{tool_names}]
Action Input: the input for the action
Observation: the result of the action
… (repeat N times)
Thought: I now know the final answer

Return ONLY a JSON array where each element has keys:
`url`, `method`, `headers`, `params`, `body`, `auth`.

Question: {input}
{agent_scratchpad}"""
    )

    # Use LangChain 0.3.x create_react_agent and AgentExecutor
    logger.info("Creating ReAct agent using LangChain 0.3.x")
    try:
        # Create agent with custom prompt
        agent = create_react_agent(llm=llm, tools=tools, prompt=react_prompt)
    except Exception as prompt_err:
        # If custom prompt fails, use default prompt
        logger.warning("create_react_agent with custom prompt failed: %s, using default prompt", prompt_err)
        agent = create_react_agent(llm=llm, tools=tools)
    
    # Create agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=False,
        handle_parsing_errors=True,
        max_iterations=10,  # Limit maximum iterations
        max_execution_time=300,  # 5 minute timeout
    )
    
    # Execute agent
    logger.info("Invoking agent executor (this may take several minutes for large HAR files)...")
    user_input = "Analyse the HAR and extract API endpoints. Return ONLY a JSON array."
    
    findings = []
    result_text = ""
    
    try:
        # Invoke agent executor using LangChain 0.3.x standard way
        # Pass callbacks via config parameter
        raw = agent_executor.invoke({"input": user_input}, config={"callbacks": [tracer]})
        
        # Extract result text
        result_text = raw.get("output", "") if isinstance(raw, dict) else str(raw)
        logger.info("Agent execution completed, output length: %d", len(result_text))
        logger.debug("Agent output (first 500 chars): %s", result_text[:500])
        
        # Try to extract JSON from result
        findings = _extract_json_from_text(result_text)
        if findings is None:
            logger.warning("Failed to extract JSON from agent output, trying to parse as-is")
            try:
                findings = json.loads(result_text) if result_text else []
            except json.JSONDecodeError:
                logger.error("Failed to parse agent output as JSON")
                findings = []
        
        if findings:
            logger.info("Successfully extracted %d endpoints from agent", len(findings))
        else:
            logger.warning("No endpoints extracted from agent output")
    except Exception as exc:
        # Agent execution failed (timeout, iteration limit, etc.), log error and use fallback
        logger.warning("Agent execution failed: %s, falling back to direct HAR extraction", exc)
        result_text = str(exc)
    
    # If agent didn't return results, use fallback to extract directly from HAR
    if not findings:
        logger.info("Attempting to extract endpoints directly from HAR (fallback method)")
        try:
            findings = _extract_endpoints_from_har(har_dict)
            if findings:
                logger.info("Extracted %d endpoints directly from HAR", len(findings))
            else:
                logger.warning("Fallback extraction returned no endpoints")
        except Exception as exc:
            logger.error("Fallback extraction failed: %s", exc)
            findings = []

    logger.info("HAR agent analysis completed. Found %d endpoints", len(findings))
    return findings, tracer.events


def _extract_endpoints_from_har(har_dict: Dict) -> List[Dict]:
    """
    Extract API endpoint information directly from HAR file (fallback when agent fails).
    
    Args:
        har_dict (Dict): HAR content (Python object).
        
    Returns:
        List[Dict]: Extracted endpoint list.
    """
    endpoints = []
    entries = har_dict.get("log", {}).get("entries", [])
    total_entries = len(entries)
    
    logger.info("Processing %d HAR entries...", total_entries)
    
    # For deduplication
    seen_urls = set()
    
    # Output progress every 100 entries or 10% of total
    progress_interval = max(100, total_entries // 10)
    
    for idx, entry in enumerate(entries):
        # Output progress
        if (idx + 1) % progress_interval == 0 or idx == 0:
            logger.info("Processing entry %d/%d (%.1f%%)...", idx + 1, total_entries, (idx + 1) * 100.0 / total_entries)
        
        try:
            request = entry.get("request", {})
            response = entry.get("response", {})
            
            url = request.get("url", "")
            method = request.get("method", "GET")
            
            # Skip static resources
            if any(url.endswith(ext) for ext in [".js", ".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot"]):
                continue
            
            # Skip data: and blob: URLs
            if url.startswith(("data:", "blob:")):
                continue
            
            # Create unique key (URL + Method)
            key = f"{method}:{url}"
            if key in seen_urls:
                continue
            seen_urls.add(key)
            
            # Extract request headers
            headers = {}
            for header in request.get("headers", []):
                name = header.get("name", "")
                value = header.get("value", "")
                if name:
                    headers[name] = value
            
            # Extract query parameters
            params = {}
            for param in request.get("queryString", []):
                name = param.get("name", "")
                value = param.get("value", "")
                if name:
                    params[name] = value
            
            # Extract request body
            body = None
            post_data = request.get("postData", {})
            if post_data:
                body_text = post_data.get("text", "")
                if body_text:
                    try:
                        body = json.loads(body_text)
                    except json.JSONDecodeError:
                        body = body_text
            
            # Extract authentication information (from headers)
            auth = None
            if "Authorization" in headers:
                auth = {"type": "Bearer", "token": headers["Authorization"]}
            elif "Cookie" in headers:
                auth = {"type": "Cookie", "value": headers["Cookie"]}
            
            endpoint = {
                "url": url,
                "method": method,
                "headers": headers,
                "params": params,
                "body": body,
                "auth": auth,
            }
            
            endpoints.append(endpoint)
            
        except Exception as e:
            logger.warning("Failed to extract endpoint from entry: %s", e)
            continue
    
    logger.info("Extraction completed: %d unique endpoints found", len(endpoints))
    return endpoints


