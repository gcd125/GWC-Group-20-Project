"""Read-only, minimized SQLite analytics export. No phone numbers or birthdays leave the database."""
from contextlib import closing
import argparse
import datetime as dt
import json
import sqlite3
from pathlib import Path


def snapshot(path):
    path=Path(path).expanduser().resolve()
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        db.execute('BEGIN')
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if 'Members' not in tables: raise ValueError('This database has no Members table.')
        def rows(table): return [dict(r) for r in db.execute('SELECT * FROM "'+table+'"')]
        members=rows('Members')
        names={m['member_id']:m.get('full_name') or ' '.join([m.get('first_name') or '',m.get('last_name') or '']).strip() for m in members}
        links=rows('Member_Discord_Links') if 'Member_Discord_Links' in tables else []
        linked={r['member_id'] for r in links}
        linked.update(m['member_id'] for m in members if m.get('discord_id'))
        discord_names={(str(r['guild_id']),str(r['discord_id'])):names.get(r['member_id'],'Member '+str(r['member_id'])) for r in links}
        events=rows('Events') if 'Events' in tables else []
        attendance=rows('Event_Participation') if 'Event_Participation' in tables else []
        giveaways=rows('Giveaways') if 'Giveaways' in tables else []
        entries=rows('Giveaway_Entries') if 'Giveaway_Entries' in tables else []
        event_rows=[]
        for e in events:
            records=[a for a in attendance if a['event_id']==e['event_id']]
            event_rows.append(dict(id=e['event_id'],name=e['event_name'],organizer=names.get(e.get('event_organizer'),'Not assigned'),points=e.get('event_points') or 0,
                registered=len({r['member_id'] for r in records}),attended=len({r['member_id'] for r in records if r.get('member_attendance')=='present'})))
        giveaway_rows=[]
        for g in giveaways:
            def display(user): return discord_names.get((str(g['guild_id']),str(user)),'Discord user '+str(user)) if user else None
            giveaway_rows.append(dict(id=g['id'],name=g['name'],prize=g.get('prize'),status=g['status'],host=display(g['host_id']) or 'Unknown',
                winner=names.get(g.get('winner_member_id')) or display(g.get('winner_id')),entries=sum(e['giveaway_id']==g['id'] for e in entries),eligible=g.get('eligible_count'),createdAt=g.get('created_at'),endsAt=g.get('ends_at'),finishedAt=g.get('finished_at')))
        return dict(version=1,capturedAt=dt.datetime.now(dt.timezone.utc).isoformat().replace('+00:00','Z'),source=path.name,testData=path.name=='gwc_test.db',
            availability=dict(events='Events' in tables,attendance='Event_Participation' in tables,giveaways='Giveaways' in tables,links='Member_Discord_Links' in tables or any('discord_id' in m for m in members)),
            members=[dict(id=m['member_id'],name=names[m['member_id']],major=m.get('major') or 'Not provided',status=m.get('member_status') or 'unknown',points=m.get('points_balance') or 0,linked=m['member_id'] in linked) for m in members],events=event_rows,giveaways=giveaway_rows)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database');parser.add_argument('output')
    args=parser.parse_args()
    Path(args.output).write_text(json.dumps(snapshot(args.database),ensure_ascii=False,indent=2))
    print('Analytics snapshot exported. Phone numbers and birthdays excluded.')
