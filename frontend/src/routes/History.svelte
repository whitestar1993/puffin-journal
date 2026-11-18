<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Entry, type Tag } from "../lib/api";
  import { formatDay } from "../lib/dates";
  import { moodEmoji, moodLabel } from "../lib/mood";

  const PAGE = 30;

  let entries = $state<Entry[]>([]);
  let tags = $state<Tag[]>([]);
  let today = $state<string>("");
  let q = $state("");
  let filter = $state<number[]>([]);
  let loading = $state(false);
  let more = $state(true);
  let error = $state("");
  let timer: ReturnType<typeof setTimeout>;
  let seq = 0;

  onMount(async () => {
    try {
      const [t, allTags] = await Promise.all([api.today(), api.tags()]);
      today = t.today;
      tags = allTags;
    } catch (err) {
      error = (err as Error).message;
    }
    await fetchPage(true);
  });

  async function fetchPage(reset: boolean) {
    const mine = ++seq;
    loading = true;
    try {
      const before = reset ? undefined : entries.at(-1)?.date;
      const page = await api.entries({ q: q.trim() || undefined, tag: filter, before, limit: PAGE });
      if (mine !== seq) return; // a newer search superseded this one
      entries = reset ? page : [...entries, ...page];
      more = page.length === PAGE;
    } catch (err) {
      error = (err as Error).message;
    } finally {
      if (mine === seq) loading = false;
    }
  }

  function onSearch() {
    clearTimeout(timer);
    timer = setTimeout(() => fetchPage(true), 250);
  }

  function toggleTag(id: number) {
    filter = filter.includes(id) ? filter.filter((x) => x !== id) : [...filter, id];
    fetchPage(true);
  }

  const snippet = (e: Entry) => e.note || e.prompt_answer || "";
</script>

<header class="page-head"><h1>History</h1></header>

<input
  class="search"
  type="search"
  placeholder="Search notes and answers"
  bind:value={q}
  oninput={onSearch}
  aria-label="Search"
/>
{#if tags.length}
  <div class="chips filter">
    {#each tags as t (t.id)}
      <button
        type="button"
        class="chip small"
        class:selected={filter.includes(t.id)}
        aria-pressed={filter.includes(t.id)}
        onclick={() => toggleTag(t.id)}>{t.name}</button
      >
    {/each}
  </div>
{/if}

{#if error}<p class="error">{error}</p>{/if}

<ul class="history">
  {#each entries as e (e.date)}
    <li>
      <a href="#/day/{e.date}" class="entry-row">
        <span class="entry-mood mood-{e.mood}" title={moodLabel(e.mood)}>{moodEmoji(e.mood)}</span>
        <span class="entry-body">
          <span class="entry-date">{formatDay(e.date, today)}</span>
          <span class="entry-meta">
            {#if e.energy}<span>⚡{e.energy}</span>{/if}
            {#if e.sleep}<span>☾{e.sleep}</span>{/if}
            {#each e.tags as t (t.id)}<span class="tag">{t.name}</span>{/each}
          </span>
          {#if snippet(e)}<span class="entry-snippet">{snippet(e)}</span>{/if}
        </span>
      </a>
    </li>
  {/each}
</ul>

{#if !loading && entries.length === 0}
  <p class="center muted">
    {q || filter.length ? "Nothing matches." : "No entries yet. Your first check-in will show up here."}
  </p>
{/if}
{#if more && entries.length > 0}
  <button type="button" class="secondary center-block" disabled={loading} onclick={() => fetchPage(false)}>
    {loading ? "…" : "Load more"}
  </button>
{/if}
