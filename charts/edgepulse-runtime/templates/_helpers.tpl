{{- define "edgepulse-runtime.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "edgepulse-runtime.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- printf "%s" $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "edgepulse-runtime.labels" -}}
app.kubernetes.io/name: {{ include "edgepulse-runtime.name" . }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}

{{- define "edgepulse-runtime.selectorLabels" -}}
app.kubernetes.io/name: {{ include "edgepulse-runtime.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{- define "edgepulse-runtime.mqttFullname" -}}
{{- printf "%s-mqtt" (include "edgepulse-runtime.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "edgepulse-runtime.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "edgepulse-runtime.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}
