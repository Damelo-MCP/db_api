"""
S3 Service para subir informes de sesiones en formato .html
"""
import boto3
from botocore.exceptions import ClientError
from datetime import datetime
from typing import Optional
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()


class S3Service:
    """Servicio para manejar subidas de archivos a S3"""

    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=os.getenv('AMAZON_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AMAZON_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AMAZON_REGION', 'us-east-1')
        )
        self.bucket_name = os.getenv('S3_BUCKET_NAME')

    def _format_html(self, html_content: str) -> str:
        """
        Formatea HTML minificado a HTML bien indentado y estructurado.

        Args:
            html_content: HTML en una sola línea o minificado

        Returns:
            HTML formateado con indentación correcta
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            formatted_html = soup.prettify()
            return formatted_html
        except Exception as e:
            print(f"Warning: Could not format HTML: {e}")
            # Si falla el formateo, devolver el original
            return html_content

    def upload_session_report(
        self,
        session_id: str,
        content: str,
        github_handle: str
    ) -> Optional[str]:
        """
        Sube un informe de sesión a S3 en formato .html

        Args:
            session_id: UUID de la sesión
            content: Contenido HTML del informe (puede estar minificado)
            github_handle: Handle de GitHub del owner

        Returns:
            URL pública del archivo en S3, o None si falla
        """
        # Generar nombre del archivo con timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_name = f"{session_id}_{timestamp}.html"

        # Path en S3: reports/{github_handle}/{session_id}_{timestamp}.html
        s3_key = f"reports/{github_handle}/{file_name}"

        try:
            # Formatear HTML antes de subir
            formatted_content = self._format_html(content)

            # Subir archivo a S3
            # El acceso público se configura via Bucket Policy (no ACL)
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=formatted_content.encode('utf-8'),
                ContentType='text/html; charset=utf-8',
                ContentDisposition='inline',
                Metadata={
                    'session_id': session_id,
                    'owner': github_handle,
                    'uploaded_at': timestamp
                }
            )

            # Generar URL pública PERMANENTE
            # Este link funciona indefinidamente mientras el archivo exista
            url = f"https://{self.bucket_name}.s3.amazonaws.com/{s3_key}"

            return url

        except ClientError as e:
            print(f"Error uploading to S3: {e}")
            return None

    def update_session_report(
        self,
        report_url: str,
        content: str,
    ) -> Optional[str]:
        """
        Sobreescribe un informe existente en S3 usando la misma key.

        Args:
            report_url: URL actual del archivo en S3
            content: Nuevo contenido HTML

        Returns:
            La misma URL si se actualizó correctamente, o None si falla
        """
        try:
            s3_key = report_url.split('.com/')[-1]
            formatted_content = self._format_html(content)

            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=formatted_content.encode('utf-8'),
                ContentType='text/html; charset=utf-8',
                ContentDisposition='inline',
            )

            return report_url

        except ClientError as e:
            print(f"Error updating S3 report: {e}")
            return None

    def delete_session_report(self, report_url: str) -> bool:
        """
        Elimina un informe de sesión de S3

        Args:
            report_url: URL del archivo a eliminar

        Returns:
            True si se eliminó exitosamente, False si falla
        """
        try:
            # Extraer key del URL
            # https://bucket.s3.amazonaws.com/reports/user/file.md -> reports/user/file.md
            s3_key = report_url.split('.com/')[-1]

            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key
            )

            return True

        except ClientError as e:
            print(f"Error deleting from S3: {e}")
            return False


# Singleton instance
s3_service = S3Service()
