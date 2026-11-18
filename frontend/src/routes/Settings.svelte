<script lang="ts">
  import { onMount } from "svelte";
  import { api, type Prompt, type Tag } from "../lib/api";

  let { onlogout }: { onlogout: () => void } = $props();

  let tags = $state<Tag[]>([]);
  let prompts = $state<Prompt[]>([]);
  let error = $state("");
  let newTag = $state("");
  let newPrompt = $state("");
  let newAnswers = $state("");

  onMount(refresh);

  async function refresh() {
    try {
      [tags, prompts] = await Promise.all([api.tags(true), api.prompts()]);
    } catch (err) {
      error = (err as Error).message;
    }
  }

  async function run(fn: () => Promise<unknown>) {
    error = "";
    try {
      await fn();
    } catch (err) {
      error = (err as Error).message;
    }
    await refresh();
  }

  const splitAnswers = (s: string) => s.split(",").map((a) => a.trim()).filter(Boolean);

  function renameTag(t: Tag, e: Event) {
    const name = (e.target as HTMLInputElement).value.trim();
    if (name && name !== t.name) run(() => api.updateTag(t.id, { name }));
  }

  function removeTag(t: Tag) {
    const msg = t.usage
      ? `"${t.name}" is used on ${t.usage} entr${t.usage === 1 ? "y" : "ies"}. Hide it from check-in? Past entries keep it.`
      : `Delete "${t.name}"?`;
    if (confirm(msg)) run(() => api.deleteTag(t.id));
  }

  function editPrompt(p: Prompt, field: "text" | "quick_answers", e: Event) {
    const v = (e.target as HTMLInputElement).value;
    if (field === "text" && v.trim() && v.trim() !== p.text) run(() => api.updatePrompt(p.id, { text: v }));
    if (field === "quick_answers") run(() => api.updatePrompt(p.id, { quick_answers: splitAnswers(v) }));
  }

  async function logout() {
    await api.logout().catch(() => {});
    onlogout();
  }
</script>

<header class="page-head"><h1>Settings</h1></header>
{#if error}<p class="error" role="alert">{error}</p>{/if}

<section class="card">
  <h2>Tags</h2>
  <p class="muted small">Most-used tags appear first on the check-in screen.</p>
  <ul class="settings-list">
    {#each tags as t (t.id)}
      <li class:archived={t.archived}>
        <input value={t.name} maxlength="40" onchange={(e) => renameTag(t, e)} aria-label="Tag name" />
        <span class="muted small">{t.usage}×</span>
        {#if t.archived}
          <button type="button" class="link" onclick={() => run(() => api.updateTag(t.id, { archived: false }))}
            >Restore</button
          >
        {:else}
          <button type="button" class="link danger" onclick={() => removeTag(t)}>Remove</button>
        {/if}
      </li>
    {/each}
  </ul>
  <form
    class="inline-add"
    onsubmit={(e) => {
      e.preventDefault();
      if (newTag.trim()) run(() => api.createTag(newTag)).then(() => (newTag = ""));
    }}
  >
    <input bind:value={newTag} maxlength="40" placeholder="New tag" aria-label="New tag" />
    <button class="secondary">Add</button>
  </form>
</section>

<section class="card">
  <h2>Daily prompts</h2>
  <p class="muted small">One active prompt is shown per day, rotating. Quick answers are comma-separated.</p>
  <ul class="settings-list prompts">
    {#each prompts as p (p.id)}
      <li class:archived={!p.active}>
        <input value={p.text} maxlength="200" onchange={(e) => editPrompt(p, "text", e)} aria-label="Prompt" />
        <input
          class="small"
          value={p.quick_answers.join(", ")}
          placeholder="quick answers, comma, separated"
          onchange={(e) => editPrompt(p, "quick_answers", e)}
          aria-label="Quick answers"
        />
        <div class="row">
          <label class="toggle">
            <input
              type="checkbox"
              checked={p.active}
              onchange={(e) => run(() => api.updatePrompt(p.id, { active: (e.target as HTMLInputElement).checked }))}
            />
            Active
          </label>
          <button
            type="button"
            class="link danger"
            onclick={() => confirm("Delete this prompt? Past answers keep its text.") && run(() => api.deletePrompt(p.id))}
            >Delete</button
          >
        </div>
      </li>
    {/each}
  </ul>
  <form
    class="stack"
    onsubmit={(e) => {
      e.preventDefault();
      if (newPrompt.trim())
        run(() => api.createPrompt(newPrompt, splitAnswers(newAnswers))).then(() => {
          newPrompt = "";
          newAnswers = "";
        });
    }}
  >
    <input bind:value={newPrompt} maxlength="200" placeholder="New prompt, e.g. What surprised you?" />
    <input bind:value={newAnswers} placeholder="Quick answers (optional, comma-separated)" />
    <button class="secondary">Add prompt</button>
  </form>
</section>

<section class="card">
  <h2>Account</h2>
  <button type="button" class="secondary" onclick={logout}>Log out</button>
</section>
