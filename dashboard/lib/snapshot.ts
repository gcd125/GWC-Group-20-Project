import { z } from 'zod';
const count = z.number().int().nonnegative();
export const snapshotSchema = z.object({
  version:z.literal(1), capturedAt:z.string().datetime(), source:z.string().min(1).max(100), testData:z.boolean(),
  availability:z.object({events:z.boolean(),attendance:z.boolean(),giveaways:z.boolean(),links:z.boolean()}),
  members:z.array(z.object({id:z.number().int(),name:z.string().max(220),major:z.string().max(200),status:z.string().max(40),points:z.number(),linked:z.boolean()})).max(100000),
  events:z.array(z.object({id:z.number().int(),name:z.string().max(300),organizer:z.string().max(220),points:z.number(),registered:count,attended:count})).max(100000),
  giveaways:z.array(z.object({id:z.number().int(),name:z.string().max(300),prize:z.string().nullable(),status:z.string().max(40),host:z.string().max(220),winner:z.string().nullable(),entries:count,eligible:count.nullable(),createdAt:z.number().nullable(),endsAt:z.number().nullable(),finishedAt:z.number().nullable()})).max(100000),
}).strict();
export type Snapshot = z.infer<typeof snapshotSchema>;
