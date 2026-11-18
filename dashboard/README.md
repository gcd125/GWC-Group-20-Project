# GWC Insights

Private analytics dashboard for the Girls Who Code @ UCF bot. React/Vinext on
Sites, with the latest validated analytics snapshot persisted in D1. The bot's
SQLite database remains the source of truth. No phone numbers or birthdays are
exported. Do not change this Site to public: data routes use its owner-private
platform boundary, including service-authenticated snapshot uploads.

Features: overview, members/search/status filter, major/status breakdowns, active
points leaders, events/attendance (when available), giveaway history/detail,
filtered CSV reports, refresh, JSON import, last-export timestamps and source
availability indicators. Zero activity and unavailable data are distinct.

See public/sync-guide.txt for export and sync commands. tools/export_analytics.py
opens SQLite read-only and reads a consistent transaction. tools/sync_analytics.py
can upload snapshots on demand or every minute without changing the bot database.
The dashboard remains available offline from the bot but data freshness requires
an exporter/sync running where the database is accessible.

Local source: /Users/gabrielap/Desktop/Projects/gwc-insights
Run npm run db:generate after schema changes; use Sites build/publish helpers.
