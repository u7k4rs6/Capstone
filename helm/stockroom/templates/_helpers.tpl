{{- define "stockroom.labels" -}}
app.kubernetes.io/part-of: stockroom
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}

{{- define "stockroom.databaseUrl" -}}
postgresql+psycopg://$(DB_USER):$(DB_PASSWORD)@{{ .Release.Name }}-postgres:5432/{{ .Values.postgres.database }}
{{- end }}
