from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from surprise_travel_planning_agent.main import handler


@pytest.mark.asyncio
async def test_handler_returns_response():
    """Test that handler accepts messages and returns a response."""
    messages = [{"role": "user", "content": "Plan a surprise trip to Paris for 5 days"}]

    # Mock itinerary response
    mock_itinerary = "DAY 1: Arrival in Paris, check into hotel...\nDAY 2: Visit Eiffel Tower...\nDAY 3: Louvre Museum...\nDAY 4: Seine River Cruise...\nDAY 5: Departure"

    with (
        patch("surprise_travel_planning_agent.main._initialized", True),
        patch("surprise_travel_planning_agent.main.run_crew", new_callable=AsyncMock, return_value=mock_itinerary),
    ):
        result = await handler(messages)

    # Verify we get a string (itinerary) back
    assert result is not None
    assert isinstance(result, str)
    assert "DAY" in result
    assert "Paris" in result


@pytest.mark.asyncio
async def test_handler_with_travel_query():
    """Test that handler processes travel planning queries correctly."""
    messages = [{"role": "user", "content": "Plan a surprise trip from New York to Tokyo for 10 days"}]

    mock_itinerary = "DAY 1: Flight from New York to Tokyo...\nDAY 2: Explore Shibuya...\nDAY 3: Visit Asakusa...\nDAY 10: Return flight..."

    with (
        patch("surprise_travel_planning_agent.main._initialized", True),
        patch(
            "surprise_travel_planning_agent.main.run_crew", new_callable=AsyncMock, return_value=mock_itinerary
        ) as mock_run,
    ):
        result = await handler(messages)

    # Verify run_crew was called with the extracted input
    mock_run.assert_called_once_with("Plan a surprise trip from New York to Tokyo for 10 days")
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.asyncio
async def test_handler_initialization():
    """Test that handler initializes crew on first call."""
    messages = [{"role": "user", "content": "Plan a weekend getaway"}]

    mock_itinerary = "DAY 1: Check in to hotel...\nDAY 2: Local activities...\nDAY 3: Departure..."

    # Start with _initialized as False to test initialization path
    with (
        patch("surprise_travel_planning_agent.main._initialized", False),
        patch("surprise_travel_planning_agent.main.initialize_crew", new_callable=AsyncMock) as mock_init,
        patch(
            "surprise_travel_planning_agent.main.run_crew", new_callable=AsyncMock, return_value=mock_itinerary
        ) as mock_run,
        patch("surprise_travel_planning_agent.main._init_lock", new_callable=MagicMock()) as mock_lock,
    ):
        # Configure the lock to work as an async context manager
        mock_lock_instance = MagicMock()
        mock_lock_instance.__aenter__ = AsyncMock(return_value=None)
        mock_lock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_lock.return_value = mock_lock_instance

        result = await handler(messages)

        # Verify initialization was called
        mock_init.assert_called_once()
        # Verify run_crew was called
        mock_run.assert_called_once_with("Plan a weekend getaway")
        # Verify we got a result
        assert result is not None
        assert isinstance(result, str)


@pytest.mark.asyncio
async def test_handler_race_condition_prevention():
    """Test that handler prevents race conditions with initialization lock."""
    messages = [{"role": "user", "content": "Test travel query"}]

    mock_itinerary = "Test itinerary content"

    # Test with multiple concurrent calls
    with (
        patch("surprise_travel_planning_agent.main._initialized", False),
        patch("surprise_travel_planning_agent.main.initialize_crew", new_callable=AsyncMock) as mock_init,
        patch("surprise_travel_planning_agent.main.run_crew", new_callable=AsyncMock, return_value=mock_itinerary),
        patch("surprise_travel_planning_agent.main._init_lock", new_callable=MagicMock()) as mock_lock,
    ):
        # Configure the lock to work as an async context manager
        mock_lock_instance = MagicMock()
        mock_lock_instance.__aenter__ = AsyncMock(return_value=None)
        mock_lock_instance.__aexit__ = AsyncMock(return_value=None)
        mock_lock.return_value = mock_lock_instance

        # Call handler twice to ensure lock is used
        await handler(messages)
        await handler(messages)

        # Verify initialize_crew was called only once (due to lock)
        mock_init.assert_called_once()


@pytest.mark.asyncio
async def test_handler_with_detailed_travel_query():
    """Test that handler can process detailed travel planning queries."""
    messages = [
        {"role": "user", "content": "Plan a surprise romantic trip to Bali for honeymoon, 7 days, luxury budget"}
    ]

    mock_itinerary = "ROMANTIC BALI HONEYMOON ITINERARY\n\nDAY 1: Arrival at Denpasar Airport..."

    with (
        patch("surprise_travel_planning_agent.main._initialized", True),
        patch("surprise_travel_planning_agent.main.run_crew", new_callable=AsyncMock, return_value=mock_itinerary),
    ):
        result = await handler(messages)

    assert result is not None
    assert isinstance(result, str)
    assert "BALI" in result.upper() or "ROMANTIC" in result.upper()


@pytest.mark.asyncio
async def test_handler_empty_user_input():
    """Test that handler handles empty user input gracefully."""
    messages = [
        {"role": "system", "content": "You are a travel planning assistant"},
        {"role": "assistant", "content": "How can I help you plan your trip?"},
        # No user message
    ]

    with patch("surprise_travel_planning_agent.main._initialized", True):
        result = await handler(messages)

    assert result is not None
    assert isinstance(result, str)
    assert "Please provide" in result


@pytest.mark.asyncio
async def test_handler_crew_exception():
    """Test that handler handles crew execution exceptions."""
    messages = [{"role": "user", "content": "Plan a trip"}]

    with (
        patch("surprise_travel_planning_agent.main._initialized", True),
        patch("surprise_travel_planning_agent.main.run_crew", new_callable=AsyncMock) as mock_run,
    ):
        # Make run_crew raise an exception
        mock_run.side_effect = Exception("Crew execution failed")

        result = await handler(messages)

    assert result is not None
    assert isinstance(result, str)
    assert "Error" in result


@pytest.mark.asyncio
async def test_handler_edge_case_malformed_messages():
    """Test handler with edge case malformed messages."""
    # Test with non-list input
    result = await handler("not a list")  # type: ignore[invalid-argument-type]
    assert result is not None
    assert isinstance(result, str)
    assert "Error" in result

    # Test with empty list
    result = await handler([])
    assert result is not None
    assert isinstance(result, str)
    assert "Please provide" in result

    # Test with list but no user messages
    result = await handler([{"role": "system", "content": "test"}])
    assert result is not None
    assert isinstance(result, str)
    assert "Please provide" in result
