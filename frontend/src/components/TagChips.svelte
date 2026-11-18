<script lang="ts">
  import { api, type Tag } from "../lib/api";

  let {
    tags = $bindable(),
    selected = $bindable(),
  }: { tags: { id: number; name: string }[]; selected: number[] } = $props();

  let adding = $state(false);
  let newName = $state("");
  let error = $state("");

  function toggle(id: number) {
    selected = selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id];
  }

  async function add(e: SubmitEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return (adding = false);
    error = "";
    try {
      const existing = tags.find((t) => t.name === name.toLowerCase());
      const tag: { id: number; name: string } = existing ?? (await api.createTag(name));
      if (!existing) tags = [...tags, tag];
      if (!selected.includes(tag.id)) selected = [...selected, tag.id];
      newName = "";
      adding = false;
    } catch (err) {
      error = (err as Error).message;
    }
  }
</script>

<fieldset class="tags">
  <legend>What was the day about?</legend>
  <div class="chips">
    {#each tags as t (t.id)}
      <button
        type="button"
        class="chip"
        class:selected={selected.includes(t.id)}
        aria-pressed={selected.includes(t.id)}
        onclick={() => toggle(t.id)}>{t.name}</button
      >
    {/each}
    {#if adding}
      <form class="chip-add" onsubmit={add}>
        <!-- svelte-ignore a11y_autofocus -->
        <input
          bind:value={newName}
          maxlength="40"
          placeholder="new tag"
          autofocus
          onblur={() => !newName && (adding = false)}
        />
      </form>
    {:else}
      <button type="button" class="chip ghost" onclick={() => (adding = true)}>+ tag</button>
    {/if}
  </div>
  {#if error}<p class="error">{error}</p>{/if}
</fieldset>
