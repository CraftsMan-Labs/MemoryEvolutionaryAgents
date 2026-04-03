<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

type QdrantMode = "local_docker" | "external";

type OnboardingStatus = {
  is_completed: boolean;
  completed_at: string | null;
  qdrant_mode: QdrantMode | null;
  obsidian_vault_path: string | null;
  external_qdrant_url: string | null;
  has_external_qdrant_api_key: boolean;
  block_reason: string | null;
};

const status = ref<OnboardingStatus | null>(null);
const loading = ref(true);
const errorMessage = ref("");
const testMessage = ref("");
const chatError = ref("");
const chatLoading = ref(false);

type CitationRecord = {
  source_path: string;
  note_path: string | null;
  chunk_id: string | null;
};

type ChatResponse = {
  answer: string;
  confidence: number;
  citations: CitationRecord[];
  retrieval_diagnostics: {
    vector_candidates: number;
    vector_kept: number;
    linkwalk_candidates: number;
    linkwalk_kept: number;
    resolved_ontology_aliases: Record<string, string>;
    resolved_taxonomy_aliases: Record<string, string>;
  };
};

const chatForm = reactive({
  query: "",
  project: "",
  tags: "",
  ontology_terms: "",
  taxonomy_tags: "",
  event_date_from: "",
  event_date_to: "",
});

const chatResponse = ref<ChatResponse | null>(null);

const canSubmitChat = computed(() => chatForm.query.trim().length > 0);

const form = reactive({
  obsidian_vault_path: "",
  qdrant_mode: "local_docker" as QdrantMode,
  external_qdrant_url: "",
  external_qdrant_api_key: "",
});

async function loadStatus(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";
  const response = await fetch("/onboarding/status");
  if (!response.ok) {
    errorMessage.value = "failed to load onboarding status";
    loading.value = false;
    return;
  }
  const payload = (await response.json()) as OnboardingStatus;
  status.value = payload;
  if (payload.obsidian_vault_path !== null) {
    form.obsidian_vault_path = payload.obsidian_vault_path;
  }
  if (payload.qdrant_mode !== null) {
    form.qdrant_mode = payload.qdrant_mode;
  }
  if (payload.external_qdrant_url !== null) {
    form.external_qdrant_url = payload.external_qdrant_url;
  }
  loading.value = false;
}

async function testConnectors(): Promise<void> {
  errorMessage.value = "";
  testMessage.value = "";
  const response = await fetch("/onboarding/test-connector", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  const payload = await response.json();
  if (!response.ok) {
    errorMessage.value = payload.detail ?? "connector test failed";
    return;
  }
  testMessage.value = payload.message;
}

async function completeOnboarding(): Promise<void> {
  errorMessage.value = "";
  const response = await fetch("/onboarding/configure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(form),
  });
  const payload = await response.json();
  if (!response.ok) {
    errorMessage.value = payload.detail ?? "failed to complete onboarding";
    return;
  }
  await loadStatus();
}

onMounted(async () => {
  await loadStatus();
});

function parseList(raw: string): string[] {
  return raw
    .split(",")
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
}

async function runChatQuery(): Promise<void> {
  if (canSubmitChat.value === false) {
    return;
  }
  chatError.value = "";
  chatLoading.value = true;
  chatResponse.value = null;

  const payload = {
    query: chatForm.query,
    filters: {
      project: chatForm.project.trim().length > 0 ? chatForm.project.trim() : null,
      tags: parseList(chatForm.tags),
      ontology_terms: parseList(chatForm.ontology_terms),
      taxonomy_tags: parseList(chatForm.taxonomy_tags),
      event_date_from:
        chatForm.event_date_from.trim().length > 0 ? chatForm.event_date_from.trim() : null,
      event_date_to:
        chatForm.event_date_to.trim().length > 0 ? chatForm.event_date_to.trim() : null,
    },
  };

  const response = await fetch("/chat/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const responsePayload = await response.json();
  if (!response.ok) {
    chatError.value = responsePayload.detail ?? "chat query failed";
    chatLoading.value = false;
    return;
  }
  chatResponse.value = responsePayload as ChatResponse;
  chatLoading.value = false;
}
</script>

<template>
  <main class="shell">
    <header class="topbar">
      <h1>Memory Evolutionary Agents</h1>
      <span class="chip">Phase 4 Chat</span>
    </header>

    <section v-if="loading" class="panel">
      <p>Loading onboarding status...</p>
    </section>

    <section v-else-if="status?.is_completed === true" class="grid-two">
      <article class="panel">
        <h2>Environment</h2>
        <p>Onboarding completed. Chat and retrieval routes are enabled.</p>
        <p>Qdrant mode: {{ status.qdrant_mode }}</p>
        <p>Vault: {{ status.obsidian_vault_path }}</p>
      </article>

      <article class="panel">
        <h2>Chat Query</h2>
        <label>
          Query
          <textarea v-model="chatForm.query" rows="3" placeholder="Ask about prior incidents, projects, or fixes" />
        </label>
        <div class="field-row">
          <label>
            Project
            <input v-model="chatForm.project" type="text" placeholder="Telemetry" />
          </label>
          <label>
            Tags (comma)
            <input v-model="chatForm.tags" type="text" placeholder="database, incident" />
          </label>
        </div>
        <div class="field-row">
          <label>
            Ontology terms (comma)
            <input v-model="chatForm.ontology_terms" type="text" placeholder="Postgres, Kafka" />
          </label>
          <label>
            Taxonomy tags (comma)
            <input v-model="chatForm.taxonomy_tags" type="text" placeholder="database, queue" />
          </label>
        </div>
        <div class="field-row">
          <label>
            Date from
            <input v-model="chatForm.event_date_from" type="date" />
          </label>
          <label>
            Date to
            <input v-model="chatForm.event_date_to" type="date" />
          </label>
        </div>
        <div class="actions">
          <button type="button" :disabled="canSubmitChat === false || chatLoading" @click="runChatQuery">
            {{ chatLoading ? "Running..." : "Run Chat Query" }}
          </button>
        </div>
        <p v-if="chatError.length > 0" class="error">{{ chatError }}</p>
      </article>

      <article class="panel full-span" v-if="chatResponse !== null">
        <h2>Answer</h2>
        <pre class="answer">{{ chatResponse.answer }}</pre>
        <p>Confidence: {{ chatResponse.confidence.toFixed(2) }}</p>
        <h3>Citations</h3>
        <ul>
          <li v-for="citation in chatResponse.citations" :key="`${citation.source_path}-${citation.chunk_id}`">
            src={{ citation.source_path }} | note={{ citation.note_path ?? "-" }} | chunk={{ citation.chunk_id ?? "-" }}
          </li>
        </ul>
        <h3>Diagnostics</h3>
        <p>
          vector {{ chatResponse.retrieval_diagnostics.vector_kept }}/{{ chatResponse.retrieval_diagnostics.vector_candidates }}
          | linkwalk {{ chatResponse.retrieval_diagnostics.linkwalk_kept }}/{{ chatResponse.retrieval_diagnostics.linkwalk_candidates }}
        </p>
      </article>
    </section>

    <section v-else class="panel">
      <h2>First-Run Onboarding</h2>
      <p>Configure your Obsidian vault and choose where Qdrant data should reside.</p>

      <label>
        Obsidian vault path
        <input v-model="form.obsidian_vault_path" type="text" placeholder="/path/to/vault" />
      </label>

      <label>
        Qdrant mode
        <select v-model="form.qdrant_mode">
          <option value="local_docker">local_docker</option>
          <option value="external">external</option>
        </select>
      </label>

      <div v-if="form.qdrant_mode === 'external'">
        <label>
          External Qdrant URL
          <input v-model="form.external_qdrant_url" type="text" placeholder="https://example.qdrant.io" />
        </label>
        <label>
          External Qdrant API key
          <input v-model="form.external_qdrant_api_key" type="password" placeholder="api key" />
        </label>
      </div>

      <div class="actions">
        <button type="button" @click="testConnectors">Test Connectors</button>
        <button type="button" @click="completeOnboarding">Complete Onboarding</button>
      </div>

      <p v-if="testMessage.length > 0" class="ok">{{ testMessage }}</p>
      <p v-if="errorMessage.length > 0" class="error">{{ errorMessage }}</p>
    </section>
  </main>
</template>

<style scoped>
.shell {
  --canvas: #0f1114;
  --surface: #161a1d;
  --raised: #1f252d;
  --border: #2a3036;
  --text: #f5f7fa;
  --muted: #a8b0ba;
  --accent: #c9754b;
  --accent-hover: #e78468;
  --focus: #f4cbb9;

  max-width: 1200px;
  margin: 24px auto;
  padding: 0 16px 24px;
  font-family: "JetBrains Mono", monospace;
  background: linear-gradient(180deg, var(--canvas), #11161d);
  color: var(--text);
}

.topbar {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: color-mix(in srgb, var(--canvas) 90%, transparent);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 16px;
}

.chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--muted);
}

.grid-two {
  display: grid;
  gap: 16px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.full-span {
  grid-column: 1 / -1;
}

.panel {
  display: grid;
  gap: 12px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 16px;
}

label {
  display: grid;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}

input,
select,
textarea,
button {
  font: inherit;
  background: var(--raised);
  color: var(--text);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 8px 10px;
}

input:focus-visible,
select:focus-visible,
textarea:focus-visible,
button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--focus);
}

button {
  background: var(--accent);
  color: #14171c;
  font-weight: 700;
  cursor: pointer;
}

button:hover {
  background: var(--accent-hover);
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.field-row {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.actions {
  display: flex;
  gap: 10px;
}

.answer {
  white-space: pre-wrap;
  background: var(--raised);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 12px;
}

.ok {
  color: #5cd0a5;
}

.error {
  color: #e78468;
}

@media (max-width: 920px) {
  .grid-two,
  .field-row {
    grid-template-columns: 1fr;
  }
 }
</style>
