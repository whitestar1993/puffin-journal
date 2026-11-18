<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Day } from "../lib/api";
  import { addDays, formatDay } from "../lib/dates";
  import { MOODS } from "../lib/mood";
  import { go } from "../lib/router.svelte";
  import Scale from "../components/Scale.svelte";
  import TagChips from "../components/TagChips.svelte";
  import PromptCard from "../components/PromptCard.svelte";

  let { date }: { date: string | null } = $props();

  const ENERGY = [1, 2, 3, 4, 5].map((v) => ({
    value: v,
    label: ["Drained", "Tired", "Okay", "Good", "Buzzing"][v - 1],
  }));
  const SLEEP = [1, 2, 3, 4, 5].map((v) => ({
    value: v,
    label: ["Terrible", "Poor", "Okay", "Good", "Great"][v - 1],
  }));

  let day = $state<Day | null>(null);
  let loadError = $state("");
  let tags = $state<{ id: number; name: string }[]>([]);

  let mood = $state<number | null>(null);
  let energy = $state<number | null>(null);
  let sleep = $state<number | null>(null);
  let tagIds = $state<number[]>([]);
  let answer = $state("");
  let skipped = $state(false);
  let note = $state("");
  let showNote = $state(false);

  let saving = $state(false);
  let status = $state<"" | "saved" | "error">("");
  let saveError = $state("");

  // A past entry whose prompt was later deleted still shows its own snapshot.
  const promptText = $derived(day?.entry?.prompt_text ?? day?.prompt?.text ?? null);
  const quickAnswers = $derived(
    day?.prompt && (!day.entry?.prompt_text || day.entry.prompt_id === day.prompt.id)
      ? day.prompt.quick_answers
      : [],
  );
  const isToday = $derived(day ? day.date === day.today : false);

  onMount(load);

  async function load() {
    try {
      const target = date ?? (await api.today()).today;
      const [d, allTags] = await Promise.all([api.day(target), api.tags()]);
      if (d.date > d.today) return go("/");
      day = d;
      const e = d.entry;
      mood = e?.mood ?? null;
      energy = e?.energy ?? null;
      sleep = e?.sleep ?? null;
      tagIds = e?.tags.map((t) => t.id) ?? [];
      answer = e?.prompt_answer ?? "";
      skipped = !!e && !e.prompt_answer;
      note = e?.note ?? "";
      showNote = !!note;
      // Archived tags already on this entry stay visible so editing doesn't drop them.
      const extra = (e?.tags ?? []).filter((t) => !allTags.some((a) => a.id === t.id));
      tags = [...allTags, ...extra];
    } catch (err) {
      loadError = (err as Error).message;
    }
  }

  async function save() {
    if (!day || mood === null) return;
    saving = true;
    status = "";
    try {
      const promptId =
        day.entry?.prompt_text && !day.entry.prompt_id ? null : (day.entry?.prompt_id ?? day.prompt?.id ?? null);
      const entry = await api.saveEntry(day.date, {
        mood,
        energy,
        sleep,
        tag_ids: tagIds,
        prompt_id: promptId,
        prompt_answer: skipped ? null : answer.trim() || null,
        note: note.trim() || null,
      });
      day = { ...day, entry };
      status = "saved";
    } catch (err) {
      status = "error";
      saveError = (err as Error).message;
    } finally {
      saving = false;
    }
  }

  async function remove() {
    if (!day?.entry || !confirm(`Delete the entry for ${formatDay(day.date, day.today)}?`)) return;
    await api.deleteEntry(day.date);
    go("/history");
  }

  function shift(n: number) {
    if (!day) return;
    const next = addDays(day.date, n);
    go(next === day.today ? "/" : `/day/${next}`);
  }

  function pickDate(e: Event) {
    const v = (e.target as HTMLInputElement).value;
    if (v && day) go(v === day.today ? "/" : `/day/${v}`);
  }

  // Any change after saving re-enables the button.
  $effect(() => {
    void [mood, energy, sleep, tagIds, answer, skipped, note];
    if (status === "saved") status = "";
  });
</script>

{#if loadError}
  <p class="error center">{loadError}</p>
{:else if !day}
  <p class="center muted">…</p>
{:else}
  <header class="day-nav">
    <button type="button" class="icon" aria-label="Previous day" onclick={() => shift(-1)}>‹</button>
    <label class="day-title">
      <span>{formatDay(day.date, day.today)}</span>
      <input type="date" value={day.date} max={day.today} onchange={pickDate} aria-label="Pick a date" />
    </label>
    <button type="button" class="icon" aria-label="Next day" disabled={isToday} onclick={() => shift(1)}
      >›</button
    >
  </header>
  {#if day.entry && status !== "saved"}<p class="muted small center">Editing saved entry</p>{/if}

  <form class="checkin" onsubmit={(e) => (e.preventDefault(), save())}>
    <Scale label="Mood" options={MOODS} bind:value={mood} big />
    <Scale label="Energy" options={ENERGY} bind:value={energy} />
    <Scale label="Sleep" options={SLEEP} bind:value={sleep} optional />
    <TagChips bind:tags bind:selected={tagIds} />

    {#if promptText}
      <PromptCard text={promptText} {quickAnswers} bind:answer bind:skipped />
    {/if}

    {#if showNote}
      <label class="note">
        <span>Note</span>
        <textarea bind:value={note} rows="4" maxlength="10000" placeholder="Anything else?"></textarea>
      </label>
    {:else}
      <button type="button" class="link" onclick={() => (showNote = true)}>+ Add a note</button>
    {/if}

    <div class="save-bar">
      {#if status === "error"}<p class="error" role="alert">{saveError}</p>{/if}
      <button class="primary big" disabled={mood === null || saving || status === "saved"}>
        {#if saving}Saving…{:else if status === "saved"}Saved ✓{:else if mood === null}Pick a mood to save{:else}Save{/if}
      </button>
    </div>
  </form>

  {#if day.entry}
    <button type="button" class="link danger center-block" onclick={remove}>Delete this entry</button>
  {/if}
{/if}
