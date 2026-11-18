import { sqliteTable, text, integer } from 'drizzle-orm/sqlite-core';
export const snapshots = sqliteTable('analytics_snapshots', {
  id: integer('id').primaryKey(), payload: text('payload').notNull(), capturedAt: text('captured_at').notNull(),
});
