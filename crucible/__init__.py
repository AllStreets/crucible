"""Automated multi-agent safety research system.

Clones real open-source AI agents from GitHub at pinned commits, builds them
into containers, checks which of those containers start in a clean sandbox, and
publishes the distribution of why the rest fail. Running the agents against each
other in a sandbox is a later phase; nothing in Phase 1 claims an agent ran.
"""
