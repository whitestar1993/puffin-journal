<script lang="ts">
  import { api, ApiError } from "../lib/api";

  let { onlogin }: { onlogin: () => void } = $props();
  let username = $state("");
  let password = $state("");
  let error = $state("");
  let busy = $state(false);

  async function submit(e: SubmitEvent) {
    e.preventDefault();
    busy = true;
    error = "";
    try {
      await api.login(username, password);
    } catch (err) {
      error =
        err instanceof ApiError && err.status === 429
          ? "Too many attempts. Wait a few minutes and try again."
          : err instanceof ApiError && err.status === 401
            ? "That didn't match."
            : "Couldn't reach the server.";
      busy = false;
      return;
    }
    // The password was right; check the browser actually kept the session cookie.
    try {
      await api.me();
      onlogin();
    } catch {
      error =
        location.protocol === "http:"
          ? "Password accepted, but your browser rejected the session cookie because this page " +
            "isn't HTTPS. Set COOKIE_SECURE=auto in .env and restart the container."
          : "Password accepted, but your browser didn't keep the session cookie. " +
            "Check that cookies are allowed for this site.";
    } finally {
      busy = false;
    }
  }
</script>

<main class="login">
  <form onsubmit={submit}>
    <div class="logo" aria-hidden="true">🙂</div>
    <h1>Puffin Journal</h1>
    <label>
      Username
      <input bind:value={username} autocomplete="username" autocapitalize="none" required />
    </label>
    <label>
      Password
      <input type="password" bind:value={password} autocomplete="current-password" required />
    </label>
    {#if error}<p class="error" role="alert">{error}</p>{/if}
    <button class="primary" disabled={busy}>{busy ? "…" : "Log in"}</button>
  </form>
</main>
