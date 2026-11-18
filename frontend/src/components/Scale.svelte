<script lang="ts">
  type Option = { value: number; label: string; emoji?: string };
  let {
    label,
    options,
    value = $bindable(),
    big = false,
    optional = false,
  }: {
    label: string;
    options: Option[];
    value: number | null;
    big?: boolean;
    optional?: boolean;
  } = $props();

  function pick(v: number) {
    // Tapping the selected value again clears it.
    value = value === v ? null : v;
  }
</script>

<fieldset class="scale" class:big>
  <legend>{label}{#if optional}<span class="muted"> · optional</span>{/if}</legend>
  <div class="scale-row">
    {#each options as o (o.value)}
      <button
        type="button"
        class="scale-btn mood-{o.value}"
        class:selected={value === o.value}
        aria-pressed={value === o.value}
        aria-label={o.label}
        onclick={() => pick(o.value)}
      >
        {#if o.emoji}<span class="emoji">{o.emoji}</span>{/if}
        <span class="lbl">{o.emoji ? o.label : o.value}</span>
      </button>
    {/each}
  </div>
</fieldset>
