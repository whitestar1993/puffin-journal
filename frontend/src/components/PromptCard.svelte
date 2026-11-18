<script lang="ts">
  let {
    text,
    quickAnswers,
    answer = $bindable(),
    skipped = $bindable(),
  }: { text: string; quickAnswers: string[]; answer: string; skipped: boolean } = $props();

  function chip(a: string) {
    answer = answer === a ? "" : a;
  }
</script>

{#if skipped}
  <button type="button" class="link" onclick={() => (skipped = false)}>Show today's prompt</button>
{:else}
  <section class="prompt card">
    <div class="prompt-head">
      <h2>{text}</h2>
      <button
        type="button"
        class="link"
        onclick={() => {
          skipped = true;
          answer = "";
        }}>Skip</button
      >
    </div>
    {#if quickAnswers.length}
      <div class="chips">
        {#each quickAnswers as a}
          <button
            type="button"
            class="chip"
            class:selected={answer === a}
            aria-pressed={answer === a}
            onclick={() => chip(a)}>{a}</button
          >
        {/each}
      </div>
    {/if}
    <input
      class="answer"
      bind:value={answer}
      maxlength="2000"
      placeholder="…or type a few words"
      aria-label="Answer"
    />
  </section>
{/if}
