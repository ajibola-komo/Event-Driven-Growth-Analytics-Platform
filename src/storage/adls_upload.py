import os
from dotenv import load_dotenv
from azure.storage.filedatalake import DataLakeServiceClient

from src.config.paths import (
    ADLS_FILE_NAMES,
    LOCAL_FILE_PATHS
)

load_dotenv()

AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_ACCOUNT_KEY = os.getenv("AZURE_STORAGE_ACCOUNT_KEY")
AZURE_FILE_SYSTEM_NAME = os.getenv("AZURE_FILE_SYSTEM_NAME")


def upload_to_adls():

    service_client = DataLakeServiceClient(
        account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net",
        credential=AZURE_STORAGE_ACCOUNT_KEY
    )

    file_system_client = service_client.get_file_system_client(
        file_system=AZURE_FILE_SYSTEM_NAME
    )

    for file_name, local_path in zip(
        ADLS_FILE_NAMES,
        LOCAL_FILE_PATHS
    ):

        file_client = file_system_client.get_file_client(file_name)

        with open(local_path, "rb") as data:

            file_client.upload_data(
                data,
                overwrite=True
            )

        print(
            f"Uploaded {local_path} "
            f"to abfss://{AZURE_FILE_SYSTEM_NAME}@"
            f"{AZURE_STORAGE_ACCOUNT_NAME}.dfs.core.windows.net/"
            f"{file_name}"
        )