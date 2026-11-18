<script lang="ts">
  import { onMount } from "svelte";
  import { api, authEvents } from "./lib/api";
  import { router } from "./lib/router.svelte";
  import Login from "./routes/Login.svelte";
  import CheckIn from "./routes/CheckIn.svelte";
  import History from "./routes/History.svelte";
  import Settings from "./routes/Settings.svelte";

  let auth = $state<"checking" | "in" | "out">("checking");

  onMount(() => {
    api.me().then(() => (auth = "in"), () => (auth = "out"));
    const onLogout = () => (auth = "out");
    authEvents.addEventListener("logout", onLogout);
    return () => authEvents.removeEventListener("logout", onLogout);
  });

  const route = $derived(router.route);
</script>

{#if auth === "checking"}
  <main class="center muted">…</main>
{:else if auth === "out"}
  <Login onlogin={() => (auth = "in")} />
{:else}
  <main>
    {#if route.name === "checkin"}
      {#key route.date}
        <CheckIn date={route.date} />
      {/key}
    {:else if route.name === "history"}
      <History />
    {:else}
      <Settings onlogout={() => (auth = "out")} />
    {/if}
  </main>
  <nav class="tabbar" aria-label="Main">
    <a href="#/" class:active={route.name === "checkin"}><span>✎</span>Check-in</a>
    <a href="#/history" class:active={route.name === "history"}><span>☰</span>History</a>
    <a href="#/settings" class:active={route.name === "settings"}><span>⚙</span>Settings</a>
  </nav>
{/if}
