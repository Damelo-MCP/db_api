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

    def _format_html(self, html_content: str, title: str = "", description: str = "") -> str:
        """
        Formatea HTML minificado a HTML bien indentado y estructurado.
        Inyecta OG meta tags si no están presentes.

        Args:
            html_content: HTML en una sola línea o minificado
            title: Título de la sesión para OG tags
            description: Descripción de la sesión para OG tags

        Returns:
            HTML formateado con indentación correcta y OG tags
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')

            # Inject OG meta tags if not present
            head = soup.find('head')
            if head and title:
                existing_og = soup.find('meta', attrs={'property': 'og:title'})
                if not existing_og:
                    og_tags = [
                        soup.new_tag('meta', attrs={'property': 'og:title', 'content': title}),
                        soup.new_tag('meta', attrs={'property': 'og:description', 'content': description or title}),
                        soup.new_tag('meta', attrs={'property': 'og:image', 'content': 'https://damelo.sh/banner.png'}),
                        soup.new_tag('meta', attrs={'property': 'og:type', 'content': 'article'}),
                        soup.new_tag('meta', attrs={'name': 'twitter:card', 'content': 'summary_large_image'}),
                        soup.new_tag('meta', attrs={'name': 'twitter:title', 'content': title}),
                        soup.new_tag('meta', attrs={'name': 'twitter:description', 'content': description or title}),
                        soup.new_tag('meta', attrs={'name': 'twitter:image', 'content': 'https://damelo.sh/banner.png'}),
                    ]
                    for tag in og_tags:
                        head.append(tag)

            # Inject "Built with Dámelo" banner
            self._inject_damelo_banner(soup)

            formatted_html = soup.prettify()
            return formatted_html
        except Exception as e:
            print(f"Warning: Could not format HTML: {e}")
            # Si falla el formateo, devolver el original
            return html_content

    def _inject_damelo_banner(self, soup: BeautifulSoup) -> None:
        """
        Inyecta un badge fijo "Built with Dámelo" al final del <body>.
        Usa CSS custom properties del documento para adaptarse a cualquier paleta.
        Idempotente: no inyecta si el badge ya existe.
        """
        # Idempotency check
        if soup.find('a', class_='damelo-badge'):
            return

        body = soup.find('body')
        if not body:
            return

        # CSS — uses document's CSS variables with neutral fallbacks
        style_tag = soup.new_tag('style')
        style_tag.string = (
            '.damelo-badge{'
            'position:fixed;bottom:16px;right:16px;z-index:9999;'
            'display:inline-flex;align-items:center;gap:8px;'
            'padding:10px 18px;'
            'background:var(--surface,#fff);'
            'color:var(--text-secondary,#5A6B7C);'
            'border:1px solid var(--border,#E2E8F0);'
            'border-radius:10px;'
            "font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;"
            'font-size:15px;font-weight:500;text-decoration:none;'
            'box-shadow:0 1px 3px rgba(0,0,0,.08);'
            'transition:box-shadow .2s,border-color .2s;'
            'opacity:.85;'
            '}'
            '.damelo-badge:hover{'
            'border-color:var(--accent,#2563EB);'
            'box-shadow:0 2px 8px rgba(0,0,0,.12);'
            'opacity:1;'
            '}'
            '@media print{.damelo-badge{display:none}}'
        )

        # Inject style into <head> if available, otherwise into <body>
        head = soup.find('head')
        if head:
            head.append(style_tag)
        else:
            body.append(style_tag)

        # Banner HTML with inline SVG (currentColor inherits --text-secondary)
        banner_html = (
            '<a class="damelo-badge" href="https://damelo.sh" '
            'target="_blank" rel="noopener noreferrer">'
            '<svg width="20" height="20" viewBox="0 0 24 24" fill="none">'
            '<path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z" fill="currentColor" '
            'opacity="0.6" stroke="currentColor" stroke-width="1.5" '
            'stroke-linejoin="round"/></svg>'
            'Built with Dámelo</a>'
        )
        banner_tag = BeautifulSoup(banner_html, 'html.parser')
        body.append(banner_tag)

    def upload_session_report(
        self,
        session_id: str,
        content: str,
        github_handle: str,
        title: str = "",
        description: str = "",
    ) -> Optional[str]:
        """
        Sube un informe de sesión a S3 en formato .html

        Args:
            session_id: UUID de la sesión
            content: Contenido HTML del informe (puede estar minificado)
            github_handle: Handle de GitHub del owner
            title: Título de la sesión (para OG tags)
            description: Descripción de la sesión (para OG tags)

        Returns:
            URL pública del archivo en S3, o None si falla
        """
        # Generar nombre del archivo con timestamp
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        file_name = f"{session_id}_{timestamp}.html"

        # Path en S3: reports/{github_handle}/{session_id}_{timestamp}.html
        s3_key = f"reports/{github_handle}/{file_name}"

        try:
            # Formatear HTML e inyectar OG tags antes de subir
            formatted_content = self._format_html(content, title=title, description=description)

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

            # URL via CloudFront custom domain (damelo.sh)
            # Clean URL without .html extension — CloudFront Function appends it
            clean_key = s3_key.removesuffix('.html')
            url = f"https://damelo.sh/{clean_key}"

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

    def archive_session_version(
        self,
        report_url: str,
        version_number: int,
    ) -> Optional[str]:
        """
        Copia server-side del reporte actual a una key versionada en S3.

        Original: reports/{handle}/{session_id}_{timestamp}.html
        Archivo:  reports/{handle}/versions/{session_id}_v{N}.html
        """
        try:
            s3_key = report_url.split('.com/')[-1]
            parts = s3_key.rsplit('/', 1)
            directory = parts[0]
            filename = parts[1]
            session_id_part = filename.split('_')[0]

            archive_key = f"{directory}/versions/{session_id_part}_v{version_number}.html"

            self.s3_client.copy_object(
                Bucket=self.bucket_name,
                CopySource={'Bucket': self.bucket_name, 'Key': s3_key},
                Key=archive_key,
                ContentType='text/html; charset=utf-8',
                ContentDisposition='inline',
            )

            return f"https://{self.bucket_name}.s3.amazonaws.com/{archive_key}"

        except ClientError as e:
            print(f"Error archiving version to S3: {e}")
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
