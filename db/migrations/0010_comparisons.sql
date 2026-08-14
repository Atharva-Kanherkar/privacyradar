-- Comparison support: denormalized taxonomy on revisions, compare product events.

alter table publication_revisions
  add column if not exists taxonomy_version text not null default '1.0.0';

alter table product_events drop constraint if exists product_events_name_check;

alter table product_events
  add constraint product_events_name_check
  check (
    name in (
      'follow',
      'unfollow',
      'radar_view',
      'evidence_open',
      'compare_start',
      'compare_complete',
      'compare_evidence'
    )
  );
