"""
Module 8: Dataproc & Spark — Concepts in Action (PySpark)
=========================================================
Reads text from GCS, counts words, writes results back to GCS — the classic job,
but demonstrating the cloud-native pattern: gs:// paths (NOT hdfs://), so compute
is disposable and storage is durable.

Submit as a Serverless batch:
  gcloud dataproc batches submit pyspark job.py \
    --region=us-central1 \
    -- gs://$PROJECT_ID-lake-raw/input gs://$PROJECT_ID-lake-curated/wordcount

Or on a cluster:
  gcloud dataproc jobs submit pyspark job.py --cluster=etl-ephemeral \
    --region=us-central1 -- gs://.../input gs://.../out
"""
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F


def main(input_path: str, output_path: str) -> None:
    spark = SparkSession.builder.appName("wordcount").getOrCreate()

    # Read straight from GCS via the built-in connector.
    lines = spark.read.text(input_path)  # column: "value"

    counts = (
        lines
        .select(F.explode(F.split(F.col("value"), r"\s+")).alias("word"))
        .where(F.col("word") != "")
        .groupBy("word")
        .count()
        .orderBy(F.desc("count"))
    )

    # Write columnar Parquet to the curated zone (partition-free demo).
    counts.write.mode("overwrite").parquet(output_path)

    # Bonus: you could write straight to BigQuery with the Spark-BigQuery connector:
    #   counts.write.format("bigquery") \
    #       .option("table", "analytics.wordcount") \
    #       .option("temporaryGcsBucket", "PROJECT-lake-raw") \
    #       .mode("overwrite").save()

    spark.stop()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: job.py <input_gcs_path> <output_gcs_path>")
    main(sys.argv[1], sys.argv[2])
