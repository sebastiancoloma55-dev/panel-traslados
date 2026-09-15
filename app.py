from pathlib import Path

src = Path("/mnt/data/Pegado text(20260915-104345).txt")
text = src.read_text(encoding="utf-8")

old = '''marker = "function init(){"
if marker not in html_content:
    st.error("No se encontró el punto de integración de sincronización en index.html.")
    st.stop()

html_content = html_content.replace(marker, central_sync + "\\n" + marker, 1)
html_content = html_content.replace(
    "Primer acceso: usuario <strong>admin</strong> · contraseña <strong>Admin123!</strong>. Por seguridad, puede cambiarla desde <strong>Usuarios</strong>.",
    "Acceso administrado centralmente. Por seguridad, cambie la contraseña desde <strong>Usuarios</strong>."
)
'''

new = '''# ============================================================
# INTEGRACION CENTRAL SUPABASE
# Se agrega AL FINAL de index.html para que las funciones
# centrales sobrescriban las funciones originales del panel.
# ============================================================

if "</body>" not in html_content:
    st.error("No se encontró </body> en index.html.")
    st.stop()

html_content = html_content.replace(
    "</body>",
    "<script>\\n" + central_sync + "\\n</script>\\n</body>",
    1
)

html_content = html_content.replace(
    "Primer acceso: usuario <strong>admin</strong> · contraseña <strong>Admin123!</strong>. Por seguridad, puede cambiarla desde <strong>Usuarios</strong>.",
    "Acceso administrado centralmente. Por seguridad, cambie la contraseña desde <strong>Usuarios</strong>."
)
'''

if old not in text:
    raise RuntimeError("No se encontró exactamente el bloque final esperado.")

corrected = text.replace(old, new, 1)

out = Path("/mnt/data/app_corregido.py")
out.write_text(corrected, encoding="utf-8")

print(f"Archivo corregido creado: {out}")
print("Se modificó únicamente la parte final que inserta central_sync.")
