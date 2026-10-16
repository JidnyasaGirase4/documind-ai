import { http } from './http'

function normalizePassage(p) {
  return {
    chunkId: p.chunk_id,
    page: p.page_number,
    snippet: p.snippet,
    keywordMatch: Boolean(p.keyword_match),
    keywordRank: p.keyword_rank ?? null,
    semanticRank: p.semantic_rank ?? null,
    similarity: p.semantic_similarity ?? null,
  }
}

function normalizeResult(r) {
  return {
    documentId: r.document_id,
    title: r.title,
    score: r.score,
    matchedOn: r.matched_on ?? [],
    passages: (r.passages ?? []).map(normalizePassage),
    pages: r.total_pages ?? null,
    category: r.category ?? null,
    tags: r.tags ?? [],
    collections: r.collections ?? [],
    role: r.role,
    createdAt: r.created_at ?? null,
  }
}

// POST /search. mode: 'hybrid' | 'keyword' | 'semantic'. Permissions are enforced by the backend.
export async function search({ query, mode = 'hybrid', collectionId, categoryId, tagId, fileType, sortBy = 'relevance', page = 1, pageSize = 10 }, { signal } = {}) {
  const body = { query, mode, sort_by: sortBy, page, page_size: pageSize }
  if (collectionId) body.collection_id = Number(collectionId)
  if (categoryId !== undefined && categoryId !== '' && categoryId !== null) body.category_id = Number(categoryId)
  if (tagId) body.tag_id = Number(tagId)
  if (fileType) body.file_type = fileType
  const { data } = await http.post('/search', body, { signal })
  return {
    query: data.query,
    mode: data.mode,
    terms: data.terms ?? [],
    phrases: data.phrases ?? [],
    items: (data.items ?? []).map(normalizeResult),
    total: data.total ?? 0,
    totalExact: data.total_exact !== false,
    page: data.page ?? page,
    pageSize: data.page_size ?? pageSize,
    pages: data.pages ?? 1,
    ranking: data.ranking ?? null,
    warnings: data.warnings ?? [],
  }
}

