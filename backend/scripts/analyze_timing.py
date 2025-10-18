#!/usr/bin/env python3
"""
Analyze agent execution timing from database.

Usage:
    python scripts/analyze_timing.py              # Show most recent session
    python scripts/analyze_timing.py --all        # Show all sessions
    python scripts/analyze_timing.py --session ID # Show specific session
"""

import asyncio
import sys
from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.database import Session, AgentOutput, SessionLog


async def analyze_session_timing(session_id: str = None, show_all: bool = False):
    """Analyze timing for one or all sessions."""
    async with AsyncSessionLocal() as db:
        # Get sessions
        if session_id:
            result = await db.execute(
                select(Session).where(Session.id == session_id)
            )
            sessions = [result.scalar_one_or_none()]
            if not sessions[0]:
                print(f"Session {session_id} not found")
                return
        elif show_all:
            result = await db.execute(
                select(Session)
                .order_by(Session.created_at.desc())
                .limit(10)
            )
            sessions = result.scalars().all()
        else:
            result = await db.execute(
                select(Session)
                .order_by(Session.created_at.desc())
                .limit(1)
            )
            sessions = [result.scalar_one_or_none()]
            if not sessions[0]:
                print("No sessions found")
                return

        for session in sessions:
            await print_session_timing(db, session)
            if len(sessions) > 1:
                print()


async def print_session_timing(db, session):
    """Print timing analysis for a single session."""
    # Session header
    print('╔' + '═' * 88 + '╗')
    print(f'║ Session: {str(session.id)[:50]:<50} ║')
    print('╠' + '═' * 88 + '╣')
    print(f'║ Status:     {session.status:<73} ║')
    print(f'║ Created:    {session.created_at}                                          ║')
    if session.updated_at:
        print(f'║ Completed:  {session.updated_at}                                          ║')
        total_time = (session.updated_at - session.created_at).total_seconds()
        print(f'║ Total Time: {total_time:>6.2f} seconds                                                       ║')
    print('╚' + '═' * 88 + '╝')
    print()

    # Get agent outputs
    result = await db.execute(
        select(AgentOutput)
        .where(AgentOutput.session_id == session.id)
        .order_by(AgentOutput.created_at)
    )
    outputs = result.scalars().all()

    if not outputs:
        print('No timing data available for this session.')
        return

    # Group by agent type
    agent_times = {}
    for output in outputs:
        agent = output.agent_type
        if agent not in agent_times:
            agent_times[agent] = []
        agent_times[agent].append({
            'duration_ms': output.duration_ms or 0,
            'timestamp': output.created_at
        })

    # Print agent timing table
    print('Agent Execution Times:')
    print('┌' + '─' * 70 + '┐')
    print(f"│ {'Agent':<25} │ {'Duration':<15} │ {'% of Total':<15} │")
    print('├' + '─' * 70 + '┤')

    total_agent_time = 0
    agent_durations = []

    for agent, times in sorted(agent_times.items()):
        # Sum all executions for this agent
        total_duration_ms = sum(t['duration_ms'] for t in times)
        duration_sec = total_duration_ms / 1000
        total_agent_time += duration_sec
        agent_durations.append((agent, duration_sec))

    # Calculate percentages
    for agent, duration in agent_durations:
        if total_agent_time > 0:
            percentage = (duration / total_agent_time) * 100
        else:
            percentage = 0
        print(f"│ {agent:<25} │ {duration:>13.2f}s │ {percentage:>13.1f}% │")

    print('├' + '─' * 70 + '┤')
    print(f"│ {'TOTAL AGENT TIME':<25} │ {total_agent_time:>13.2f}s │ {100.0:>13.1f}% │")

    if session.updated_at and session.created_at:
        total_session = (session.updated_at - session.created_at).total_seconds()
        overhead = total_session - total_agent_time
        overhead_pct = (overhead / total_session * 100) if total_session > 0 else 0

        print(f"│ {'OVERHEAD':<25} │ {overhead:>13.2f}s │ {overhead_pct:>13.1f}% │")
        print(f"│ {'SESSION TOTAL':<25} │ {total_session:>13.2f}s │          100.0% │")

    print('└' + '─' * 70 + '┘')

    # Print detailed breakdown
    print()
    print('Detailed Agent Timeline:')
    print('┌' + '─' * 88 + '┐')
    print(f"│ {'Agent':<25} │ {'Start Time':<25} │ {'Duration':<15} │")
    print('├' + '─' * 88 + '┤')

    for output in outputs:
        agent = output.agent_type
        duration_sec = (output.duration_ms or 0) / 1000
        timestamp_str = str(output.created_at)[:19]
        print(f"│ {agent:<25} │ {timestamp_str:<25} │ {duration_sec:>13.2f}s │")

    print('└' + '─' * 88 + '┘')


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='Analyze agent execution timing')
    parser.add_argument('--session', '-s', help='Specific session ID to analyze')
    parser.add_argument('--all', '-a', action='store_true', help='Show all sessions')
    args = parser.parse_args()

    asyncio.run(analyze_session_timing(
        session_id=args.session,
        show_all=args.all
    ))


if __name__ == '__main__':
    main()
