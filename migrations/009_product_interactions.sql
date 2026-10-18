-- Aggregate public behavior only. No IP, visitor/session keys, URLs, text or raw coordinates.
CREATE TABLE product_daily_counts (
  day date NOT NULL,
  event_name text NOT NULL CHECK (event_name IN ('page_view','navigation_click','section_open','cv_link_open','contact_link_open','company_link_open')),
  section text NOT NULL CHECK (section IN ('home','about','work','filomena','stack','education','cv','contact')),
  locale text NOT NULL CHECK (locale IN ('en','es')),
  target text NOT NULL CHECK (target IN ('','en','es','email','linkedin','github','rampy','teamcubation','cooperativa-obrera','independent')),
  country text NOT NULL CHECK (country='unknown' OR country ~ '^[A-Z]{2}$'),
  count integer NOT NULL CHECK (count BETWEEN 1 AND 10000),
  PRIMARY KEY(day,event_name,section,locale,target,country)
);
-- Existing seven-day facts have no reliable country attribution.
INSERT INTO product_daily_counts SELECT day,event_name,section,locale,target,'unknown',count FROM product_event_counts;

CREATE TABLE product_interaction_counts (
  day date NOT NULL,
  event_name text NOT NULL CHECK (event_name IN ('public_click','section_exposure')),
  section text NOT NULL CHECK (section IN ('home','about','work','filomena','stack','education','cv','contact')),
  locale text NOT NULL CHECK (locale IN ('en','es')),
  region_id text NOT NULL CHECK (region_id IN (
    'site-header','site-footer','home-featured','home-experience','home-about','home-education','home-contact',
    'about-story','about-focus','about-principles','about-opportunities',
    'work-rampy','work-teamcubation','work-cooperativa','work-independent','work-projects',
    'filomena-problem','filomena-approach','filomena-outcomes','filomena-evidence','stack-catalogue','stack-scope',
    'education-degree','education-curriculum','education-credentials','education-evidence',
    'cv-downloads','cv-summary','contact-channels','contact-resume'
  )),
  CHECK (region_id IN ('site-header','site-footer') OR region_id LIKE section || '-%'),
  layout_revision text NOT NULL CHECK (layout_revision='portfolio-v1'),
  viewport text NOT NULL CHECK (viewport IN ('mobile','tablet','desktop')),
  cell_x smallint NOT NULL,
  cell_y smallint NOT NULL,
  count integer NOT NULL CHECK (count BETWEEN 1 AND 10000),
  CHECK ((event_name='public_click' AND cell_x BETWEEN 0 AND 7 AND cell_y BETWEEN 0 AND 7)
      OR (event_name='section_exposure' AND cell_x=-1 AND cell_y=-1)),
  PRIMARY KEY(day,event_name,section,locale,region_id,layout_revision,viewport,cell_x,cell_y)
);

CREATE TABLE product_collection_status (
  singleton boolean PRIMARY KEY DEFAULT true CHECK (singleton),
  first_observed_at timestamptz NOT NULL,
  last_observed_at timestamptz NOT NULL,
  CHECK (first_observed_at<=last_observed_at)
);
INSERT INTO product_collection_status(singleton,first_observed_at,last_observed_at)
  SELECT true,min(day)::timestamp AT TIME ZONE 'UTC',greatest(max(day)::timestamp AT TIME ZONE 'UTC',coalesce((SELECT max(received_at) FROM product_event_dedupe),max(day)::timestamp AT TIME ZONE 'UTC'))
  FROM product_event_counts HAVING count(*)>0;
