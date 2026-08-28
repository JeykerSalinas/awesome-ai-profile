# Backend observability and chat errors

The backend writes structured JSON logs to standard output. Azure Container Apps
collects that stream as console logs; when the Container Apps environment uses a
Log Analytics destination, those records are retained in
`ContainerAppConsoleLogs_CL` and remain searchable after a replica restarts.

Logs deliberately exclude prompts, conversation text, uploaded-document content,
and API keys. Known secret formats and the configured `GOOGLE_API_KEY` are
redacted before a record is written.

## Correlating a visitor error

Every HTTP request receives an `X-Request-ID`. Chat failures expose only a short
reference to the visitor and write the same identifier as `request_id` in the
backend log. The backend also records a safe classification in `error_code`:

- `billing_unavailable`
- `provider_authentication_failed`
- `provider_quota_exceeded`
- `provider_access_denied`
- `provider_temporarily_unavailable`
- `chat_generation_failed`

The frontend turns this contract into a localized alert, offers retry only when
the failure may be transient, and displays the reference needed to find the
matching backend record.

## Live logs

With the Azure values configured in `.env.make`:

```bash
make logs-back
```

This follows application logs. Container provisioning and image failures are
separate system logs:

```bash
make logs-back-system
```

## Retained logs in Azure

In Azure Portal, open the Container App, then **Monitoring > Logs**. This query
lists recent application errors and parses each JSON message:

```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "awesome-ai-profile-api"
| extend Event = parse_json(Log_s)
| where tostring(Event.level) == "ERROR"
| project TimeGenerated,
          ErrorCode=tostring(Event.error_code),
          RequestId=tostring(Event.request_id),
          Message=tostring(Event.message),
          ProviderDetail=tostring(Event.provider_detail),
          RevisionName_s
| order by TimeGenerated desc
```

To find the exact incident shown in the frontend, replace the reference below:

```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "awesome-ai-profile-api"
| extend Event = parse_json(Log_s)
| where tostring(Event.request_id) startswith "ERROR_REFERENCE"
| project TimeGenerated, Event, RevisionName_s
| order by TimeGenerated desc
```

If `ContainerAppConsoleLogs_CL` is unavailable, verify that the Container Apps
environment log destination is Log Analytics. The live stream alone is useful
for debugging but is not the retained log store.

Microsoft references:

- https://learn.microsoft.com/azure/container-apps/log-streaming
- https://learn.microsoft.com/azure/container-apps/log-monitoring
