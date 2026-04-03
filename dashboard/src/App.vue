<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from "vue";

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

type LoadState = "idle" | "loading" | "success" | "error";

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
  request_id: string | null;
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

type JobHealth = {
  total_runs: number;
  running_runs: number;
  failed_runs: number;
  latest_run_id: number | null;
  latest_run_status: string | null;
};

type ConnectorHealth = {
  total_sources: number;
  healthy_sources: number;
  unhealthy_sources: number;
};

type FreshnessStatus = {
  latest_run_at: string | null;
  minutes_since_last_run: number | null;
  stale_threshold_minutes: number;
  is_stale: boolean;
};

type UsageTrendPoint = {
  date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  cost_amount: string;
};

type UsageMetrics = {
  range_days: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  total_cost_amount: string;
  currency: string;
  trend: UsageTrendPoint[];
};

type PipelineTrendPoint = {
  date: string;
  chunks_created: number;
  memories_created: number;
};

type PipelineMetrics = {
  range_days: number;
  total_runs: number;
  total_memories: number;
  total_chunks: number;
  avg_chunks_per_memory: number;
  trend: PipelineTrendPoint[];
};

type FileProgressRecord = {
  file_run_id: number;
  run_id: number;
  source_id: number;
  source_path: string;
  file_path: string;
  stage: string;
  status: string;
  error_code: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string | null;
};

type RunFilesResponse = {
  run_id: number;
  files: FileProgressRecord[];
  stage_summary: { stage: string; total: number }[];
  status_summary: { status: string; total: number }[];
};

type FileTimelineResponse = {
  file_run_id: number;
  events: {
    id: number;
    run_id: number;
    file_run_id: number;
    source_id: number;
    file_path: string;
    from_stage: string | null;
    to_stage: string;
    status: string;
    duration_ms: number | null;
    error_code: string | null;
    error_message: string | null;
    recorded_at: string;
  }[];
};

const phase5State = ref<LoadState>("idle");
const phase5Error = ref("");
const jobHealth = ref<JobHealth | null>(null);
const connectorHealth = ref<ConnectorHealth | null>(null);
const freshness = ref<FreshnessStatus | null>(null);
const usageMetrics = ref<UsageMetrics | null>(null);
const pipelineMetrics = ref<PipelineMetrics | null>(null);
const runFilesState = ref<LoadState>("idle");
const runFilesError = ref("");
const runFiles = ref<FileProgressRecord[]>([]);
const selectedFile = ref<FileProgressRecord | null>(null);
const selectedTimeline = ref<FileTimelineResponse | null>(null);
const deadLetterCount = ref(0);
const progressFilters = reactive({
  runId: "",
  stage: "",
  status: "",
  sourceId: "",
  fromDate: "",
  toDate: "",
});
const progressStream = ref<EventSource | null>(null);
const progressStreamRunId = ref<number | null>(null);

const canSubmitChat = computed(() => chatForm.query.trim().length > 0);

const form = reactive({
  obsidian_vault_path: "",
  qdrant_mode: "local_docker" as QdrantMode,
  external_qdrant_url: "",
  external_qdrant_api_key: "",
});

type OnboardingPayload = {
  obsidian_vault_path: string;
  qdrant_mode: QdrantMode;
  external_qdrant_url: string | null;
  external_qdrant_api_key: string | null;
};

function buildOnboardingPayload(): OnboardingPayload {
  const vaultPath = form.obsidian_vault_path.trim();
  if (form.qdrant_mode === "external") {
    const externalUrl = form.external_qdrant_url.trim();
    const externalApiKey = form.external_qdrant_api_key.trim();
    return {
      obsidian_vault_path: vaultPath,
      qdrant_mode: form.qdrant_mode,
      external_qdrant_url: externalUrl.length > 0 ? externalUrl : null,
      external_qdrant_api_key: externalApiKey.length > 0 ? externalApiKey : null,
    };
  }
  return {
    obsidian_vault_path: vaultPath,
    qdrant_mode: form.qdrant_mode,
    external_qdrant_url: null,
    external_qdrant_api_key: null,
  };
}

function formatApiError(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.length > 0) {
    return detail;
  }
  if (Array.isArray(detail)) {
    return JSON.stringify(detail);
  }
  return fallback;
}

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
  const requestPayload = buildOnboardingPayload();
  const response = await fetch("/onboarding/test-connector", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestPayload),
  });
  const payload = await response.json();
  if (!response.ok) {
    errorMessage.value = formatApiError(payload.detail, "connector test failed");
    return;
  }
  testMessage.value = payload.message;
}

async function completeOnboarding(): Promise<void> {
  errorMessage.value = "";
  const requestPayload = buildOnboardingPayload();
  const response = await fetch("/onboarding/configure", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(requestPayload),
  });
  const payload = await response.json();
  if (!response.ok) {
    errorMessage.value = formatApiError(payload.detail, "failed to complete onboarding");
    return;
  }
  await loadStatus();
  await loadPhase5Widgets();
  await loadRunFiles();
}

onMounted(async () => {
  await loadStatus();
  if (status.value?.is_completed === true) {
    await loadPhase5Widgets();
    await loadRunFiles();
  }
});

onBeforeUnmount(() => {
  if (progressStream.value !== null) {
    progressStream.value.close();
  }
  progressStream.value = null;
  progressStreamRunId.value = null;
});

async function loadPhase5Widgets(): Promise<void> {
  phase5State.value = "loading";
  phase5Error.value = "";
  try {
    const [jobsResponse, connectorsResponse, freshnessResponse, usageResponse, pipelineResponse] = await Promise.all([
      fetch("/status/jobs"),
      fetch("/status/connectors"),
      fetch("/status/freshness"),
      fetch("/metrics/usage?days=7"),
      fetch("/metrics/pipeline?days=7"),
    ]);
    if (
      !jobsResponse.ok ||
      !connectorsResponse.ok ||
      !freshnessResponse.ok ||
      !usageResponse.ok ||
      !pipelineResponse.ok
    ) {
      throw new Error("failed to load phase 5 status widgets");
    }
    jobHealth.value = (await jobsResponse.json()) as JobHealth;
    connectorHealth.value = (await connectorsResponse.json()) as ConnectorHealth;
    freshness.value = (await freshnessResponse.json()) as FreshnessStatus;
    usageMetrics.value = (await usageResponse.json()) as UsageMetrics;
    pipelineMetrics.value = (await pipelineResponse.json()) as PipelineMetrics;
    phase5State.value = "success";
  } catch (error) {
    phase5State.value = "error";
    phase5Error.value = error instanceof Error ? error.message : "phase 5 metrics failed";
  }
}

function resolveRunId(): number | null {
  const raw = progressFilters.runId.trim();
  if (raw.length > 0) {
    const parsed = Number.parseInt(raw, 10);
    if (Number.isNaN(parsed) === false && parsed > 0) {
      return parsed;
    }
  }
  return jobHealth.value?.latest_run_id ?? null;
}

async function loadRunFiles(): Promise<void> {
  runFilesState.value = "loading";
  runFilesError.value = "";
  selectedTimeline.value = null;
  const runId = resolveRunId();
  if (runId === null) {
    runFilesState.value = "success";
    runFiles.value = [];
    if (progressStream.value !== null) {
      progressStream.value.close();
      progressStream.value = null;
      progressStreamRunId.value = null;
    }
    return;
  }
  subscribeRunStream(runId);

  const params = new URLSearchParams();
  if (progressFilters.stage.trim().length > 0) {
    params.set("stage", progressFilters.stage.trim());
  }
  if (progressFilters.status.trim().length > 0) {
    params.set("status", progressFilters.status.trim());
  }
  if (progressFilters.sourceId.trim().length > 0) {
    params.set("source_id", progressFilters.sourceId.trim());
  }
  if (progressFilters.fromDate.trim().length > 0) {
    params.set("from_date", `${progressFilters.fromDate.trim()}T00:00:00Z`);
  }
  if (progressFilters.toDate.trim().length > 0) {
    params.set("to_date", `${progressFilters.toDate.trim()}T23:59:59Z`);
  }
  params.set("limit", "200");

  try {
    const filesResponse = await fetch(`/runs/${runId}/files?${params.toString()}`);
    const deadLetterResponse = await fetch("/status/dead-letter?limit=1");
    if (!filesResponse.ok) {
      throw new Error("failed to load run files");
    }
    const payload = (await filesResponse.json()) as RunFilesResponse;
    runFiles.value = payload.files;
    if (deadLetterResponse.ok) {
      const dead = (await deadLetterResponse.json()) as { file_run_id: number }[];
      deadLetterCount.value = dead.length;
    }
    runFilesState.value = "success";
  } catch (error) {
    runFilesError.value = error instanceof Error ? error.message : "run file load failed";
    runFilesState.value = "error";
  }
}

function subscribeRunStream(runId: number): void {
  if (progressStreamRunId.value === runId && progressStream.value !== null) {
    return;
  }
  if (progressStream.value !== null) {
    progressStream.value.close();
  }
  const stream = new EventSource(`/runs/${runId}/stream`);
  stream.addEventListener("progress", () => {
    void loadRunFiles();
  });
  progressStream.value = stream;
  progressStreamRunId.value = runId;
}

async function openFileTimeline(fileRow: FileProgressRecord): Promise<void> {
  selectedFile.value = fileRow;
  const response = await fetch(`/files/${fileRow.file_run_id}/timeline`);
  if (!response.ok) {
    runFilesError.value = "failed to load file timeline";
    return;
  }
  selectedTimeline.value = (await response.json()) as FileTimelineResponse;
}

async function retryFile(fileRow: FileProgressRecord): Promise<void> {
  const response = await fetch(`/files/${fileRow.file_run_id}/retry`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ requested_by: "dashboard" }),
  });
  if (!response.ok) {
    runFilesError.value = "manual retry failed";
    return;
  }
  await loadRunFiles();
}

const usageCurrency = computed(() => usageMetrics.value?.currency ?? "USD");
const usageCost = computed(() => usageMetrics.value?.total_cost_amount ?? "0");

const processSegments = computed(() => {
  const runs = jobHealth.value?.total_runs ?? 0;
  const failed = jobHealth.value?.failed_runs ?? 0;
  const running = jobHealth.value?.running_runs ?? 0;
  const completed = Math.max(0, runs - failed - running);
  const denominator = Math.max(1, runs);
  return [
    {
      label: "completed",
      value: completed,
      width: Math.max(15, Math.round((completed / denominator) * 100)),
      tone: "tone-ok",
    },
    {
      label: "running",
      value: running,
      width: Math.max(15, Math.round((running / denominator) * 100)),
      tone: "tone-warn",
    },
    {
      label: "failed",
      value: failed,
      width: Math.max(15, Math.round((failed / denominator) * 100)),
      tone: "tone-error",
    },
  ];
});

const tokenBars = computed(() => {
  const trend = usageMetrics.value?.trend ?? [];
  const maxTokens = Math.max(1, ...trend.map((item) => item.total_tokens));
  return trend.map((item) => ({
    label: item.date.slice(5),
    value: item.total_tokens,
    height: Math.max(6, Math.round((item.total_tokens / maxTokens) * 120)),
  }));
});

const chunkBars = computed(() => {
  const trend = pipelineMetrics.value?.trend ?? [];
  const maxChunks = Math.max(1, ...trend.map((item) => item.chunks_created));
  return trend.map((item) => ({
    label: item.date.slice(5),
    chunks: item.chunks_created,
    memories: item.memories_created,
    height: Math.max(6, Math.round((item.chunks_created / maxChunks) * 120)),
  }));
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
      <span class="chip">Phase 6 Progress + Reliability</span>
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
        <h2>Operational Status</h2>
        <p v-if="phase5State === 'loading'" class="muted">Loading status cards...</p>
        <p v-else-if="phase5State === 'error'" class="error">{{ phase5Error }}</p>
        <div v-else-if="phase5State === 'success'" class="kpi-grid">
          <div class="kpi-card">
            <span class="kpi-label">runs</span>
            <strong class="kpi-value">{{ jobHealth?.total_runs ?? 0 }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">failed runs</span>
            <strong class="kpi-value">{{ jobHealth?.failed_runs ?? 0 }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">healthy sources</span>
            <strong class="kpi-value">{{ connectorHealth?.healthy_sources ?? 0 }}</strong>
          </div>
          <div class="kpi-card" :class="freshness?.is_stale === true ? 'kpi-stale' : ''">
            <span class="kpi-label">freshness</span>
            <strong class="kpi-value">
              {{ freshness?.minutes_since_last_run ?? "-" }}m
            </strong>
          </div>
          <div class="kpi-card full-kpi">
            <span class="kpi-label">token usage (7d)</span>
            <strong class="kpi-value">{{ usageMetrics?.total_tokens ?? 0 }}</strong>
          </div>
          <div class="kpi-card full-kpi">
            <span class="kpi-label">cost (7d)</span>
            <strong class="kpi-value">{{ usageCurrency }} {{ usageCost }}</strong>
          </div>
        </div>
      </article>

      <article class="panel full-span">
        <h2>Analytics Dashboard</h2>
        <p class="muted">Token consumption, process outcomes, and chunk generation trends.</p>
        <div class="kpi-grid analytics-kpis">
          <div class="kpi-card">
            <span class="kpi-label">total tokens (7d)</span>
            <strong class="kpi-value">{{ usageMetrics?.total_tokens ?? 0 }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">total processes</span>
            <strong class="kpi-value">{{ pipelineMetrics?.total_runs ?? 0 }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">chunks created</span>
            <strong class="kpi-value">{{ pipelineMetrics?.total_chunks ?? 0 }}</strong>
          </div>
          <div class="kpi-card">
            <span class="kpi-label">avg chunks/memory</span>
            <strong class="kpi-value">{{ (pipelineMetrics?.avg_chunks_per_memory ?? 0).toFixed(2) }}</strong>
          </div>
        </div>

        <div class="chart-grid">
          <section class="chart-panel">
            <h3>Process Outcomes</h3>
            <div class="stacked-row">
              <div
                v-for="segment in processSegments"
                :key="segment.label"
                class="segment"
                :class="segment.tone"
                :style="{ width: `${segment.width}%` }"
              >
                {{ segment.label }}: {{ segment.value }}
              </div>
            </div>
          </section>

          <section class="chart-panel">
            <h3>Tokens by Day</h3>
            <div class="bar-chart" v-if="tokenBars.length > 0">
              <div v-for="bar in tokenBars" :key="bar.label" class="bar-wrap">
                <div class="bar token-bar" :style="{ height: `${bar.height}px` }" :title="`${bar.value} tokens`" />
                <span class="bar-label">{{ bar.label }}</span>
              </div>
            </div>
            <p v-else class="muted">No token events yet.</p>
          </section>

          <section class="chart-panel">
            <h3>Chunks by Day</h3>
            <div class="bar-chart" v-if="chunkBars.length > 0">
              <div v-for="bar in chunkBars" :key="bar.label" class="bar-wrap">
                <div
                  class="bar chunk-bar"
                  :style="{ height: `${bar.height}px` }"
                  :title="`${bar.chunks} chunks, ${bar.memories} memories`"
                />
                <span class="bar-label">{{ bar.label }}</span>
              </div>
            </div>
            <p v-else class="muted">No chunk activity yet.</p>
          </section>
        </div>
      </article>

      <article class="panel full-span">
        <h2>File Progress</h2>
        <div class="field-row">
          <label>
            Run ID (default latest)
            <input v-model="progressFilters.runId" type="text" placeholder="latest run" />
          </label>
          <label>
            Source ID
            <input v-model="progressFilters.sourceId" type="text" placeholder="any" />
          </label>
        </div>
        <div class="field-row">
          <label>
            Stage
            <input v-model="progressFilters.stage" type="text" placeholder="failed | completed" />
          </label>
          <label>
            Status
            <input v-model="progressFilters.status" type="text" placeholder="queued | failed | success" />
          </label>
        </div>
        <div class="field-row">
          <label>
            Date from
            <input v-model="progressFilters.fromDate" type="date" />
          </label>
          <label>
            Date to
            <input v-model="progressFilters.toDate" type="date" />
          </label>
        </div>
        <div class="actions">
          <button type="button" @click="loadRunFiles">Refresh Files</button>
          <span class="muted">dead-letter files: {{ deadLetterCount }}</span>
        </div>
        <p v-if="runFilesState === 'loading'" class="muted">Loading file progress...</p>
        <p v-else-if="runFilesState === 'error'" class="error">{{ runFilesError }}</p>
        <p v-else-if="runFiles.length === 0" class="muted">No files matched current filters.</p>
        <table v-else class="progress-table">
          <thead>
            <tr>
              <th>file</th>
              <th>stage</th>
              <th>status</th>
              <th>error</th>
              <th>action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in runFiles" :key="item.file_run_id">
              <td>{{ item.file_path }}</td>
              <td>{{ item.stage }}</td>
              <td>{{ item.status }}</td>
              <td>{{ item.error_code ?? "-" }}</td>
              <td class="row-actions">
                <button type="button" @click="openFileTimeline(item)">Timeline</button>
                <button type="button" :disabled="item.status === 'success'" @click="retryFile(item)">
                  Retry
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </article>

      <article class="panel full-span" v-if="selectedTimeline !== null && selectedFile !== null">
        <h2>File Timeline</h2>
        <p class="muted">{{ selectedFile.file_path }}</p>
        <ul>
          <li v-for="event in selectedTimeline.events" :key="event.id">
            {{ event.recorded_at }} | {{ event.from_stage ?? "-" }} -> {{ event.to_stage }} | {{ event.status }}
            <span v-if="event.error_code !== null">| {{ event.error_code }}</span>
          </li>
        </ul>
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
        <p class="muted">Request ID: {{ chatResponse.request_id ?? "-" }}</p>
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

.muted {
  color: var(--muted);
}

.kpi-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.kpi-card {
  display: grid;
  gap: 8px;
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 12px;
  background: var(--raised);
}

.kpi-label {
  color: var(--muted);
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.kpi-value {
  font-size: 22px;
  line-height: 1;
}

.full-kpi {
  grid-column: 1 / -1;
}

.kpi-stale {
  border-color: var(--accent-hover);
}

.analytics-kpis {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.chart-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.chart-panel {
  display: grid;
  gap: 10px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--raised);
  padding: 12px;
}

.stacked-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.segment {
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  border: 1px solid var(--border);
}

.tone-ok {
  background: color-mix(in srgb, #5cd0a5 20%, transparent);
}

.tone-warn {
  background: color-mix(in srgb, #e0b460 20%, transparent);
}

.tone-error {
  background: color-mix(in srgb, #e78468 20%, transparent);
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  min-height: 150px;
}

.bar-wrap {
  display: grid;
  gap: 6px;
  justify-items: center;
}

.bar {
  width: 16px;
  border-radius: 8px 8px 4px 4px;
  border: 1px solid var(--border);
}

.token-bar {
  background: color-mix(in srgb, var(--accent) 70%, #f4cbb9);
}

.chunk-bar {
  background: color-mix(in srgb, #5cd0a5 70%, #b8f0da);
}

.bar-label {
  font-size: 11px;
  color: var(--muted);
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

.progress-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.progress-table th,
.progress-table td {
  border-bottom: 1px solid var(--border);
  text-align: left;
  padding: 8px;
  vertical-align: top;
}

.row-actions {
  display: flex;
  gap: 8px;
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
  .field-row,
  .chart-grid,
  .analytics-kpis {
    grid-template-columns: 1fr;
  }
 }
</style>
