# backend/src/mcps/mcp-sync/sync_mcps.py
import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Ajustar PYTHONPATH para importar el backend
current_dir = Path(__file__).resolve().parent
backend_dir = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(backend_dir))

from src.services.mcps.client.client_manager import MCPClientManager

load_dotenv()

TEST_USER = os.getenv("USUARIO_TEST")

# Mapeo de qué MCPs pertenecen a qué Agente
AGENT_MCP_MAPPING = {
    "koda": ["github", "context7", "files"],
    "nexus": ["notion", "google_calendar"]
}

# Rutas absolutas a los archivos AGENT.md
AGENT_PATHS = {
    "koda": backend_dir / "src" / "services" / "agent" / "Koda" / "AGENT.md",
    "nexus": backend_dir / "src" / "services" / "agent" / "nexus" / "AGENT.md"
}

async def generate_mcp_markdown(manager: MCPClientManager, provider: str) -> str:
    """Levanta el MCP, extrae las herramientas y devuelve filas de Markdown."""
    try:
        print(f"🔌 Conectando a {provider}...")
        client = manager.get_client(provider)
        
        # Simulamos un usuario de prueba para poder extraer las tools
        # (Para Context7 no importa, para otros quizás necesite token temporal)
        
        async with client as active_client:
            # Obtenemos las StructuredTools de LangChain (Ya con el esquema Pydantic y Descripción)
            tools = await active_client.get_langchain_tools()
            
            if not tools:
                return f"| **{provider}** | *(No tools exposed)* |"

            tools_html = ""
            for t in tools:
                # Extraemos la descripción truncada para que la tabla no sea gigante
                desc = t.description.split("\n")[0] if t.description else ""
                if len(desc) > 80: desc = desc[:77] + "..."
                tools_html += f"**{t.name}**: {desc}<br>"

            return f"| **{provider}** | {tools_html} |"

    except Exception as e:
        print(f"Error conectando a {provider}: {e}")
        return f"| **{provider}** | *(Error connecting: {e})* |"


async def update_agent_md(agent_name: str, mcps: list[str]):
    """Actualiza la tabla en el AGENT.md correspondiente."""
    md_path = AGENT_PATHS.get(agent_name)
    if not md_path or not md_path.exists():
        print(f"No se encontró el AGENT.md para {agent_name} en {md_path}")
        return

    # Usamos user_id genérico para extraer los metadatos (no ejecutaremos las tools)
    manager = MCPClientManager(user_id=TEST_USER)

    # Generamos las filas de la tabla
    rows = []
    for mcp in mcps:
        row = await generate_mcp_markdown(manager, mcp)
        rows.append(row)

    # Construimos la sección de Markdown
    mcp_section = "### Connected MCP Integrations\n\n"
    mcp_section += "The following external tools are injected into this agent via MCP:\n\n"
    mcp_section += "| Integration | Available Tools |\n"
    mcp_section += "|-------------|-----------------|\n"
    mcp_section += "\n".join(rows)
    mcp_section += "\n"

    # Leemos el archivo actual
    content = md_path.read_text(encoding="utf-8")

    # Reemplazamos la sección vieja o la agregamos al final
    start_marker = "### Connected MCP Integrations"
    
    if start_marker in content:
        # Lógica para reemplazar hasta el siguiente ## (o final de archivo)
        parts = content.split(start_marker)
        before = parts[0]
        after = parts[1]
        
        # Buscamos dónde termina la sección actual de MCP (siguiente heading)
        next_heading_idx = after.find("\n## ")
        if next_heading_idx != -1:
            after = after[next_heading_idx:]
        else:
            after = "" # Era la última sección
            
        new_content = before + mcp_section + after
    else:
        # Agregamos al final si no existía
        new_content = content + "\n" + mcp_section

    # Guardamos los cambios
    md_path.write_text(new_content, encoding="utf-8")
    print(f"✅ Documentación de {agent_name.upper()} actualizada exitosamente.")


async def main():
    print("🚀 Iniciando MCP Sync...\n")
    for agent, mcps in AGENT_MCP_MAPPING.items():
        print(f"Sincronizando MCPs para: {agent}")
        await update_agent_md(agent, mcps)
        print("-" * 50)
    print("\n Sincronización completada.")

if __name__ == "__main__":
    asyncio.run(main())