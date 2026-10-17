-- No visitor/session keys, client timestamps, URLs, text, IP or raw payloads.
CREATE TABLE product_event_dedupe (
  event_id uuid PRIMARY KEY,
  received_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX product_event_dedupe_received ON product_event_dedupe(received_at);
CREATE TABLE product_event_counts (
  day date NOT NULL,
  event_name text NOT NULL CHECK (event_name IN ('page_view','navigation_click','section_open','cv_link_open','contact_link_open','company_link_open')),
  section text NOT NULL CHECK (section IN ('home','about','work','filomena','stack','education','cv','contact')),
  locale text NOT NULL CHECK (locale IN ('en','es')),
  target text NOT NULL CHECK (target IN ('','en','es','email','linkedin','github','rampy','teamcubation','cooperativa-obrera','independent')),
  count integer NOT NULL CHECK (count BETWEEN 1 AND 10000),
  PRIMARY KEY (day,event_name,section,locale,target)
);
