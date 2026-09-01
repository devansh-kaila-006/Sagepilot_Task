import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from langchain_core.messages import HumanMessage, AIMessage
from app.agent import classifier_node, agent_node

@pytest.mark.asyncio
async def test_classifier_node_wake():
    with patch("app.agent.ChatGoogleGenerativeAI") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=AIMessage(content="WAKE"))
        MockLLM.return_value = mock_llm_instance
        
        state = {
            "recent_activities": "test activity",
            "messages": [HumanMessage(content="Hello")]
        }
        
        result = await classifier_node(state)
        assert result["wake_decision"] == "WAKE"

@pytest.mark.asyncio
async def test_classifier_node_sleep():
    with patch("app.agent.ChatGoogleGenerativeAI") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_instance.ainvoke = AsyncMock(return_value=AIMessage(content="SLEEP"))
        MockLLM.return_value = mock_llm_instance
        
        state = {
            "recent_activities": "test activity",
            "messages": [HumanMessage(content="Hello")]
        }
        
        result = await classifier_node(state)
        assert result["wake_decision"] == "SLEEP"

@pytest.mark.asyncio
async def test_agent_node():
    with patch("app.agent.ChatGoogleGenerativeAI") as MockLLM:
        mock_llm_instance = MagicMock()
        mock_llm_with_tools = MagicMock()
        
        # Simulate LLM returning a tool call
        mock_ai_message = AIMessage(content="", tool_calls=[{"name": "tool_sleep", "args": {"hours": 10}, "id": "call_1"}])
        mock_llm_with_tools.ainvoke = AsyncMock(return_value=mock_ai_message)
        
        mock_llm_instance.bind_tools.return_value = mock_llm_with_tools
        MockLLM.return_value = mock_llm_instance
        
        state = {
            "order_id": "ORD-123",
            "supervisor_instruction": "test",
            "recent_activities": "none",
            "messages": [HumanMessage(content="Hello")]
        }
        
        result = await agent_node(state)
        assert len(result["messages"]) == 1
        assert result["messages"][0].tool_calls[0]["name"] == "tool_sleep"
