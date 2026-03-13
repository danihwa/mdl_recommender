-- Run this in Supabase SQL editor after schema.sql
-- Provides semantic similarity search with optional filters

create or replace function match_documents (
  query_embedding vector(1536),
  match_threshold float,
  match_count int,
  filter_year int default 1900,
  filter_score float default 0.0,
  exclude_id int default -1
)
returns table (
  id int,
  mdl_id int,        -- ← useful for building MDL links
  title text,
  native_title text,
  year int,
  synopsis text,
  mdl_score numeric,
  genres text[],     -- ← useful for display
  tags text[],       -- ← useful for display
  watchers int,      -- ← useful for sorting/filtering
  mdl_url text,      -- ← useful for linking
  similarity float
)
language sql stable
as $$
  select
    id,
    mdl_id,
    title,
    native_title,
    year,
    synopsis,
    mdl_score,
    genres,
    tags,
    watchers,
    mdl_url,
    1 - (dramas.embedding <=> query_embedding) as similarity
  from dramas
  where 1 - (dramas.embedding <=> query_embedding) > match_threshold
    and dramas.year >= filter_year
    and dramas.mdl_score >= filter_score
    and dramas.id != exclude_id
  order by dramas.embedding <=> query_embedding asc
  limit match_count;
$$;