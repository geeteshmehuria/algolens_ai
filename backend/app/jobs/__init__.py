"""Standalone background jobs run by an external scheduler (cron / Task Scheduler).

Kept out of the FastAPI process on purpose: uvicorn --reload spawns multiple
workers, so an in-process timer would fire once per worker and duplicate imports.
"""
