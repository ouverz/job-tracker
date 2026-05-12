import json
import re
from collections import Counter
from fastapi import APIRouter, Query
from typing import Optional
from ..database import db

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

VALID_STATUSES = {"new", "applied", "rejected", "pending", "archived", "interview"}

# ── Vocabulary ────────────────────────────────────────────────────────────────
# Maps lowercase alias → canonical display name.
# Rules:
#  - NO generic cloud parent terms (aws, azure, gcp) — only named services.
#    If a JD just says "Azure experience" without a service, it's not actionable.
#  - Multiple aliases share a canonical  (pyspark / spark / apache spark → "Apache Spark")
#  - Longer aliases are sorted first in the compiled regex so they match before substrings.

VOCAB: dict[str, str] = {
    # ── Programming languages ─────────────────────────────────────────────────
    "python":                   "Python",
    "sql":                      "SQL",
    "scala":                    "Scala",
    "java":                     "Java",
    "rust":                     "Rust",
    "typescript":               "TypeScript",
    "javascript":               "JavaScript",
    "bash":                     "Bash/Shell",
    "shell scripting":          "Bash/Shell",
    "shell script":             "Bash/Shell",

    # ── AWS services ──────────────────────────────────────────────────────────
    # (no generic "aws" entry — only named services)
    "amazon redshift":          "AWS Redshift",
    "redshift":                 "AWS Redshift",
    "amazon s3":                "AWS S3",
    "aws s3":                   "AWS S3",
    "s3":                       "AWS S3",
    "aws glue":                 "AWS Glue",
    "glue":                     "AWS Glue",
    "aws lambda":               "AWS Lambda",
    "lambda":                   "AWS Lambda",
    "aws dms":                  "AWS DMS",
    "database migration service": "AWS DMS",
    "amazon emr":               "AWS EMR",
    "aws emr":                  "AWS EMR",
    "emr":                      "AWS EMR",
    "amazon athena":            "AWS Athena",
    "aws athena":               "AWS Athena",
    "athena":                   "AWS Athena",
    "amazon kinesis":           "Kinesis",
    "kinesis":                  "Kinesis",
    "aws step functions":       "Step Functions",
    "step functions":           "Step Functions",
    "amazon sagemaker":         "SageMaker",
    "sagemaker":                "SageMaker",
    "amazon dynamodb":          "DynamoDB",
    "dynamodb":                 "DynamoDB",
    "amazon rds":               "AWS RDS",
    "aws rds":                  "AWS RDS",
    "amazon ec2":               "AWS EC2",
    "aws ec2":                  "AWS EC2",
    "amazon ecs":               "AWS ECS",
    "aws ecs":                  "AWS ECS",
    "amazon eks":               "AWS EKS",
    "aws eks":                  "AWS EKS",
    "cloudwatch":               "AWS CloudWatch",
    "aws cloudwatch":           "AWS CloudWatch",
    "aws cdk":                  "AWS CDK",
    "cdk":                      "AWS CDK",

    # ── Azure services ────────────────────────────────────────────────────────
    # (no generic "azure" entry — only named services)
    "azure synapse analytics":  "Azure Synapse",
    "azure synapse":            "Azure Synapse",
    "azure data factory":       "Azure Data Factory",
    "adf":                      "Azure Data Factory",
    "azure data lake storage":  "ADLS",
    "azure data lake":          "ADLS",
    "adls":                     "ADLS",
    "azure databricks":         "Databricks",
    "azure machine learning":   "Azure ML",
    "azure ml":                 "Azure ML",
    "azure openai":             "OpenAI",
    "azure cosmos db":          "Cosmos DB",
    "cosmos db":                "Cosmos DB",
    "azure sql database":       "Azure SQL",
    "azure sql":                "Azure SQL",
    "azure blob storage":       "Azure Blob Storage",
    "azure blob":               "Azure Blob Storage",
    "azure stream analytics":   "Azure Stream Analytics",
    "azure service bus":        "Azure Service Bus",
    "azure functions":          "Azure Functions",
    "azure devops":             "Azure DevOps",
    "azure event hubs":         "Event Hubs",
    "event hubs":               "Event Hubs",
    "microsoft fabric":         "Microsoft Fabric",
    "ms fabric":                "Microsoft Fabric",

    # ── GCP services ─────────────────────────────────────────────────────────
    # (no generic "gcp" / "google cloud" entry — only named services)
    "google bigquery":          "BigQuery",
    "bigquery":                 "BigQuery",
    "google dataflow":          "Dataflow",
    "dataflow":                 "Dataflow",
    "google dataproc":          "Dataproc",
    "dataproc":                 "Dataproc",
    "google pub/sub":           "Pub/Sub",
    "pub/sub":                  "Pub/Sub",
    "vertex ai":                "Vertex AI",
    "google cloud storage":     "GCS",
    "gcs":                      "GCS",
    "cloud run":                "Cloud Run",
    "google cloud functions":   "Cloud Functions",
    "bigtable":                 "Bigtable",
    "cloud spanner":            "Cloud Spanner",
    "spanner":                  "Cloud Spanner",

    # ── Data & analytics platforms ────────────────────────────────────────────
    "databricks":               "Databricks",
    "databricks certified":     "Databricks",
    "snowflake":                "Snowflake",
    "sap datasphere":           "SAP Datasphere",
    "sap hana":                 "SAP HANA",
    "hana":                     "SAP HANA",
    "sap bw":                   "SAP BW",
    "delta lake":               "Delta Lake",
    "apache iceberg":           "Apache Iceberg",
    "iceberg":                  "Apache Iceberg",
    "apache hudi":              "Apache Hudi",
    "hudi":                     "Apache Hudi",

    # ── BI / visualisation ────────────────────────────────────────────────────
    "power bi":                 "Power BI",
    "powerbi":                  "Power BI",
    "tableau":                  "Tableau",
    "looker":                   "Looker",
    "looker studio":            "Looker Studio",
    "qliksense":                "Qlik Sense",
    "qlik sense":               "Qlik Sense",
    "qlikview":                 "QlikView",
    "qlik":                     "Qlik",
    "metabase":                 "Metabase",
    "grafana":                  "Grafana",
    "apache superset":          "Superset",
    "superset":                 "Superset",
    "microstrategy":            "MicroStrategy",

    # ── Orchestration / transformation ────────────────────────────────────────
    "apache airflow":           "Airflow",
    "airflow":                  "Airflow",
    "prefect":                  "Prefect",
    "dagster":                  "Dagster",
    "luigi":                    "Luigi",
    "dbt":                      "dbt",
    "data build tool":          "dbt",
    "mage":                     "Mage",
    "kedro":                    "Kedro",

    # ── Stream / batch processing ─────────────────────────────────────────────
    "apache spark":             "Apache Spark",
    "pyspark":                  "Apache Spark",
    "spark streaming":          "Apache Spark",
    "spark":                    "Apache Spark",
    "apache flink":             "Apache Flink",
    "flink":                    "Apache Flink",
    "apache kafka":             "Kafka",
    "kafka streams":            "Kafka",
    "kafka":                    "Kafka",
    "apache beam":              "Apache Beam",
    "beam":                     "Apache Beam",

    # ── Databases ─────────────────────────────────────────────────────────────
    "postgresql":               "PostgreSQL",
    "postgres":                 "PostgreSQL",
    "mysql":                    "MySQL",
    "mongodb":                  "MongoDB",
    "apache cassandra":         "Cassandra",
    "cassandra":                "Cassandra",
    "redis":                    "Redis",
    "elasticsearch":            "Elasticsearch",
    "opensearch":               "OpenSearch",
    "microsoft sql server":     "MS SQL Server",
    "ms sql server":            "MS SQL Server",
    "sql server":               "MS SQL Server",
    "mssql":                    "MS SQL Server",
    "oracle database":          "Oracle DB",
    "oracle db":                "Oracle DB",
    "oracle":                   "Oracle DB",
    "clickhouse":               "ClickHouse",
    "duckdb":                   "DuckDB",

    # ── ML / AI frameworks ────────────────────────────────────────────────────
    "tensorflow":               "TensorFlow",
    "pytorch":                  "PyTorch",
    "scikit-learn":             "Scikit-learn",
    "sklearn":                  "Scikit-learn",
    "keras":                    "Keras",
    "mlflow":                   "MLflow",
    "kubeflow":                 "Kubeflow",
    "mlops":                    "MLOps",
    "hugging face":             "Hugging Face",
    "huggingface":              "Hugging Face",
    "langchain":                "LangChain",
    "llamaindex":               "LlamaIndex",
    "llama index":              "LlamaIndex",
    "openai":                   "OpenAI",
    "rag":                      "RAG",
    "retrieval augmented":      "RAG",
    "large language model":     "LLMs",
    "llm":                      "LLMs",
    "vector database":          "Vector DB",
    "vector store":             "Vector DB",
    "vector db":                "Vector DB",

    # ── ML concepts ───────────────────────────────────────────────────────────
    "machine learning":         "Machine Learning",
    "deep learning":            "Deep Learning",
    "natural language processing": "NLP",
    "nlp":                      "NLP",
    "computer vision":          "Computer Vision",
    "reinforcement learning":   "Reinforcement Learning",
    "feature engineering":      "Feature Engineering",
    "a/b testing":              "A/B Testing",
    "ab testing":               "A/B Testing",
    "statistics":               "Statistics",
    "statistical modeling":     "Statistics",

    # ── DevOps / infrastructure ───────────────────────────────────────────────
    "docker":                   "Docker",
    "kubernetes":               "Kubernetes",
    "k8s":                      "Kubernetes",
    "terraform":                "Terraform",
    "ci/cd":                    "CI/CD",
    "continuous integration":   "CI/CD",
    "github actions":           "GitHub Actions",
    "jenkins":                  "Jenkins",
    "gitlab ci":                "GitLab CI",
    "gitlab":                   "GitLab CI",
    "helm":                     "Helm",
    "ansible":                  "Ansible",
    "infrastructure as code":   "IaC",
    "iac":                      "IaC",

    # ── ETL / integration tools ───────────────────────────────────────────────
    "fivetran":                 "Fivetran",
    "airbyte":                  "Airbyte",
    "informatica":              "Informatica",
    "ssis":                     "SSIS",
    "talend":                   "Talend",
    "etl":                      "ETL/ELT",
    "elt":                      "ETL/ELT",

    # ── Data architecture concepts ────────────────────────────────────────────
    "data modeling":            "Data Modeling",
    "data modelling":           "Data Modeling",
    "data mesh":                "Data Mesh",
    "data lakehouse":           "Data Lakehouse",
    "lakehouse":                "Data Lakehouse",
    "data warehouse":           "Data Warehouse",
    "data lake":                "Data Lake",
    "star schema":              "Star Schema",
    "data vault":               "Data Vault",
    "dimensional modeling":     "Dimensional Modeling",
    "dimensional modelling":    "Dimensional Modeling",
    "medallion architecture":   "Medallion Architecture",

    # ── Soft / domain skills ──────────────────────────────────────────────────
    "stakeholder management":   "Stakeholder Management",
    "project management":       "Project Management",
    "agile":                    "Agile",
    "scrum":                    "Scrum",
    "data governance":          "Data Governance",
    "data quality":             "Data Quality",
    "data privacy":             "Data Privacy",
    "gdpr":                     "GDPR",
    "rest api":                 "REST API",
    "restful":                  "REST API",
    "api":                      "REST API",
    "microservices":            "Microservices",
}

# ── German language pattern ───────────────────────────────────────────────────
_GERMAN_LEVEL_RE = re.compile(
    r"\b(?:German|Deutsch)\b.{0,40}?([A-C][12][+]?)",
    re.IGNORECASE,
)
_GERMAN_MENTION_RE = re.compile(r"\b(?:German|Deutsch)\b", re.IGNORECASE)

_BLOCKER_LEVELS = {"B2", "B2+", "C1", "C1+", "C2"}


def _german_canonical(text: str) -> str | None:
    m = _GERMAN_LEVEL_RE.search(text)
    if m:
        level = m.group(1).upper()
        return "German B2+" if level in _BLOCKER_LEVELS else f"German {level}"
    if _GERMAN_MENTION_RE.search(text):
        return "German language"
    return None


# ── Vocab regex (compiled once at import) ─────────────────────────────────────
_sorted_aliases = sorted(VOCAB.keys(), key=len, reverse=True)
_VOCAB_RE = re.compile(
    r"\b(" + "|".join(re.escape(k) for k in _sorted_aliases) + r")\b",
    re.IGNORECASE,
)


# ── Entity extraction ─────────────────────────────────────────────────────────

def _extract_entities(text: str) -> list[str]:
    """
    Extract all known entities from one raw gap/strength string.
    May return multiple entities per string (e.g. "Databricks and MLflow" → 2).
    Strings with no vocab match return [] and are silently dropped.
    """
    results: list[str] = []
    seen: set[str] = set()

    german = _german_canonical(text)
    if german and german not in seen:
        results.append(german)
        seen.add(german)

    for match in _VOCAB_RE.finditer(text):
        canonical = VOCAB[match.group(1).lower()]
        if canonical not in seen:
            results.append(canonical)
            seen.add(canonical)

    return results


# ── Aggregation ───────────────────────────────────────────────────────────────

def _aggregate(raw_items: list[str]) -> list[dict]:
    counter: Counter = Counter()
    for raw in raw_items:
        for canonical in _extract_entities(raw):
            counter[canonical] += 1
    return [{"text": t, "count": c} for t, c in counter.most_common(30)]


# ── Route ─────────────────────────────────────────────────────────────────────

@router.get("/gaps")
def get_gap_analysis(
    min_score: float = Query(0, ge=0, le=100),
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
):
    conditions = ["cv_score_breakdown IS NOT NULL"]
    params = []

    if min_score > 0:
        conditions.append("cv_score >= ?")
        params.append(min_score)

    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip() in VALID_STATUSES]
        if statuses:
            placeholders = ",".join("?" * len(statuses))
            conditions.append(f"status IN ({placeholders})")
            params.extend(statuses)

    if source:
        sources = [s.strip() for s in source.split(",") if s.strip()]
        if sources:
            placeholders = ",".join("?" * len(sources))
            conditions.append(f"source IN ({placeholders})")
            params.extend(sources)

    where = "WHERE " + " AND ".join(conditions)

    with db() as conn:
        rows = conn.execute(
            f"SELECT cv_score_breakdown FROM jobs {where}", params
        ).fetchall()

    raw_gaps: list[str] = []
    raw_strengths: list[str] = []
    for row in rows:
        try:
            bd = json.loads(row["cv_score_breakdown"])
            raw_gaps.extend(item for item in bd.get("gaps", []) if item)
            raw_strengths.extend(item for item in bd.get("strengths", []) if item)
        except Exception:
            continue

    return {
        "total_scored": len(rows),
        "gaps": _aggregate(raw_gaps),
        "strengths": _aggregate(raw_strengths),
    }
