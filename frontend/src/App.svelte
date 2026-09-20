<script>
  import { streamSearchAgent, postJSON, getHealth } from './lib/api.js';

  let tab = $state('search');
  let health = $state(null);
  getHealth().then((h) => (health = h)).catch(() => {});

  // --- Search agent ---
  let question = $state('What year was KMITL founded? Cite the source URL you read.');
  let defended = $state(true);
  let events = $state([]);
  let final = $state(null);
  let running = $state(false);
  let agentErr = $state('');

  async function runAgent() {
    running = true; events = []; final = null; agentErr = '';
    try {
      await streamSearchAgent(question, defended, (ev) => {
        if (ev.type === 'final') final = ev;
        else if (ev.type === 'error') agentErr = ev.message;
        else events = [...events, ev];
      });
    } catch (e) {
      agentErr = String(e);
    } finally {
      running = false;
    }
  }

  // --- Browser: render vs fetch ---
  let renderUrl = $state('https://quotes.toscrape.com/js/');
  let render = $state(null);
  let renderBusy = $state(false);
  let renderErr = $state('');
  async function runRender() {
    renderBusy = true; render = null; renderErr = '';
    try { render = await postJSON('/api/browser/render', { url: renderUrl }); }
    catch (e) { renderErr = String(e); }
    finally { renderBusy = false; }
  }

  // --- Browser: login automation ---
  let username = $state('student');
  let password = $state('kmitl-demo');
  let automation = $state(null);
  let autoBusy = $state(false);
  let autoErr = $state('');
  async function runAuto() {
    autoBusy = true; automation = null; autoErr = '';
    try { automation = await postJSON('/api/browser/automate', { username, password }); }
    catch (e) { autoErr = String(e); }
    finally { autoBusy = false; }
  }
</script>

<main>
  <header>
    <h1>Agentic Web Search &amp; Automation</h1>
    <p class="sub">KMITL · LLM Lecture 12 — an agent that searches the web, reads pages,
      cites its sources, and drives a real browser.</p>
    {#if health}
      <div class="health">
        <span class:ok={health.tavily_key_set} class:bad={!health.tavily_key_set}>
          Tavily key {health.tavily_key_set ? '✓' : '✗ (set TAVILY_API_KEY)'}</span>
        <span class:ok={health.llm_key_set} class:bad={!health.llm_key_set}>
          LLM key {health.llm_key_set ? '✓' : '✗ (set LLM_API_KEY)'}</span>
        <span class="muted">model: {health.model}</span>
      </div>
    {/if}
  </header>

  <nav class="tabs">
    <button class:active={tab === 'search'} onclick={() => (tab = 'search')}>1 · Search agent</button>
    <button class:active={tab === 'browser'} onclick={() => (tab = 'browser')}>2 · Browser automation</button>
  </nav>

  {#if tab === 'search'}
    <section>
      <p class="hint">The model decides when to <code>web_search</code> and which page to
        <code>fetch_page</code>, then answers from the text it actually read — with a citation
        your code recorded at fetch time (it can't be faked).</p>

      <label class="field">Question
        <input bind:value={question} placeholder="Ask something that needs fresh, real-world facts…" />
      </label>
      <label class="toggle">
        <input type="checkbox" bind:checked={defended} />
        Defended (treat fetched pages as untrusted data — turn <b>off</b> to see a page hijack the agent)
      </label>
      <button class="run" onclick={runAgent} disabled={running}>
        {running ? 'Running…' : 'Run agent'}</button>

      {#if agentErr}<p class="err">{agentErr}</p>{/if}

      {#if events.length || final}
        <div class="trace">
          {#each events as ev}
            {#if ev.type === 'act'}
              <div class="act"><b>ACT</b> <code>{ev.tool}({ev.args})</code></div>
            {:else if ev.type === 'obs'}
              <div class="obs"><b>OBS</b> <span>{ev.preview}</span></div>
            {/if}
          {/each}
        </div>
      {/if}

      {#if final}
        <div class="answer">
          <h3>Answer</h3>
          <p>{final.answer}</p>
          {#if final.citations?.length}
            <h4>Sources (recorded by the code, at fetch time)</h4>
            <ul>{#each final.citations as c}<li><a href={c} target="_blank" rel="noopener">{c}</a></li>{/each}</ul>
          {:else}
            <p class="muted">No page was fetched — an ungrounded answer you should distrust.</p>
          {/if}
        </div>
      {/if}
    </section>
  {:else}
    <section>
      <h2>Why a browser? JavaScript-rendered pages</h2>
      <p class="hint">A plain HTTP GET (what <code>fetch_page</code> does) returns the raw HTML.
        If a page builds its content with JavaScript, that content isn't there yet — only a real
        browser runs the JS and reveals it.</p>
      <label class="field">URL
        <input bind:value={renderUrl} />
      </label>
      <button class="run" onclick={runRender} disabled={renderBusy}>
        {renderBusy ? 'Launching browser…' : 'Compare plain GET vs browser'}</button>
      {#if renderErr}<p class="err">{renderErr}</p>{/if}
      {#if render}
        <div class="cols">
          <div class="col">
            <h4>Plain GET (no JavaScript)</h4>
            <div class="metric">{render.raw_len} chars of readable text</div>
            <pre>{render.raw_preview}</pre>
          </div>
          <div class="col">
            <h4>Browser render (Playwright)</h4>
            <div class="metric">{render.rendered_len} chars
              {#if render.quotes_visible_after_render != null}· {render.quotes_visible_after_render} quotes visible{/if}</div>
            <pre>{render.rendered_preview}</pre>
          </div>
        </div>
      {/if}

      <h2 style="margin-top:2rem">Multi-step automation: log in &amp; read a value</h2>
      <p class="hint">The four browser primitives — <code>goto</code>, <code>fill</code>,
        <code>click</code>, <code>read</code> — sequenced into a login flow on
        <code>quotes.toscrape.com</code> (it accepts any credentials).</p>
      <div class="row">
        <label class="field">Username <input bind:value={username} /></label>
        <label class="field">Password <input bind:value={password} /></label>
      </div>
      <button class="run" onclick={runAuto} disabled={autoBusy}>
        {autoBusy ? 'Automating…' : 'Run login automation'}</button>
      {#if autoErr}<p class="err">{autoErr}</p>{/if}
      {#if automation}
        <div class="trace">
          {#each automation.trace as st}
            <div class="act"><b>ACT</b> <code>{st.act}</code> &nbsp;<span class="obsinline">OBS {st.obs}</span></div>
          {/each}
        </div>
        <div class="answer"><b>{automation.logged_in ? '✓' : '✗'}</b> {automation.result}</div>
      {/if}
    </section>
  {/if}

  <footer>
    <span class="muted">Safety note: fetched page text is treated as untrusted <i>data</i>, never
      commands — the core defense against prompt injection (Lecture 12 §7).</span>
  </footer>
</main>

<style>
  :global(body) { margin: 0; background: #0f1216; color: #e6e9ef;
    font: 15px/1.55 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
  main { max-width: 860px; margin: 0 auto; padding: 2rem 1.25rem 4rem; }
  h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
  .sub { color: #9aa4b2; margin: 0 0 1rem; }
  .health { display: flex; gap: 1rem; flex-wrap: wrap; font-size: .82rem; margin-bottom: 1rem; }
  .health .ok { color: #4ade80; } .health .bad { color: #f87171; }
  .muted { color: #7b8494; }
  .tabs { display: flex; gap: .5rem; border-bottom: 1px solid #2a2f3a; margin-bottom: 1.25rem; }
  .tabs button { background: none; border: none; color: #9aa4b2; padding: .6rem .9rem;
    cursor: pointer; font-size: .95rem; border-bottom: 2px solid transparent; }
  .tabs button.active { color: #e6e9ef; border-bottom-color: #6366f1; }
  h2 { font-size: 1.15rem; margin: 1rem 0 .5rem; }
  .hint { color: #9aa4b2; font-size: .9rem; }
  code { background: #1b212b; padding: .1rem .35rem; border-radius: 4px; font-size: .85em; }
  .field { display: block; margin: .8rem 0; font-size: .85rem; color: #9aa4b2; }
  .field input { display: block; width: 100%; box-sizing: border-box; margin-top: .3rem;
    background: #171c24; border: 1px solid #2a2f3a; color: #e6e9ef; padding: .55rem .7rem;
    border-radius: 8px; font-size: .95rem; }
  .row { display: flex; gap: 1rem; } .row .field { flex: 1; }
  .toggle { display: flex; gap: .5rem; align-items: flex-start; font-size: .85rem;
    color: #9aa4b2; margin: .6rem 0; }
  .run { background: #6366f1; color: white; border: none; padding: .6rem 1.2rem;
    border-radius: 8px; font-size: .95rem; cursor: pointer; }
  .run:disabled { opacity: .55; cursor: default; }
  .trace { margin: 1rem 0; border: 1px solid #2a2f3a; border-radius: 10px; overflow: hidden; }
  .act, .obs { padding: .5rem .75rem; font-size: .85rem; border-bottom: 1px solid #20252f; }
  .act { background: #151a22; } .act b { color: #818cf8; }
  .obs { background: #12161d; color: #9aa4b2; } .obs b { color: #4ade80; }
  .obs span { word-break: break-word; } .obsinline { color: #7b8494; }
  .answer { margin-top: 1rem; background: #12181f; border: 1px solid #2a2f3a;
    border-radius: 10px; padding: 1rem 1.15rem; }
  .answer h3, .answer h4 { margin: 0 0 .4rem; } .answer h4 { margin-top: .8rem; font-size: .85rem; color: #9aa4b2; }
  .answer a { color: #7dd3fc; word-break: break-all; }
  .cols { display: flex; gap: 1rem; } .col { flex: 1; min-width: 0; }
  .col h4 { margin: .5rem 0 .3rem; }
  .metric { font-size: .8rem; color: #4ade80; margin-bottom: .4rem; }
  pre { background: #12161d; border: 1px solid #2a2f3a; border-radius: 8px; padding: .6rem;
    font-size: .78rem; white-space: pre-wrap; word-break: break-word; max-height: 220px;
    overflow: auto; color: #c8cfda; }
  .err { color: #f87171; font-size: .88rem; }
  footer { margin-top: 2.5rem; border-top: 1px solid #2a2f3a; padding-top: 1rem; font-size: .8rem; }
  @media (max-width: 620px) { .cols, .row { flex-direction: column; } }
</style>
