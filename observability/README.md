# Existing-stack integration

This project reuses the Compose stack at `/Users/subrat/Desktop/workflow/docker-compose.yml`. It must not start Prometheus, Grafana, Loki, Promtail, Tempo, or Phoenix.

## Attachment points

- External Docker network: `workflow_default`.
- Prometheus: add the scrape jobs in `prometheus/scrape-jobs.yml` to the existing `scrape_configs`, then reload/restart only that existing Prometheus service.
- Grafana: copy or link `grafana/llm-serving.json` into the existing provisioned dashboard directory. It uses the existing datasource UIDs.
- Loki: no configuration change. Existing Promtail discovers gateway container logs through Docker labels.
- Tempo: gateway OTLP target is `http://tempo:4317` on the shared network.
- Phoenix: controlled LLM spans target `http://phoenix:4317` on the shared network. Phoenix and Tempo both expose 4317 inside their own containers; Docker DNS names disambiguate them.
- Host-native vLLM-Metal: from containers, use `host.docker.internal:8101` for A or `host.docker.internal:8102` for B.

## Data boundaries

Prometheus labels are bounded to pipeline, endpoint, and outcome. Prompt text and request IDs never become metric labels. Loki receives safe structured operational events. Tempo receives request-path spans. Phoenix receives controlled benchmark prompt IDs, model identity, token counts, and evaluation attributes; arbitrary user prompt content is disabled by default.

These files are proposals only in Phase 1. The existing stack has not been edited.
