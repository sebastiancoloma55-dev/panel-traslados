import { createClient } from "npm:@supabase/supabase-js@2.45.4";

const supabase = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);

const JWT_SECRET = Deno.env.get("APP_JWT_SECRET")!;

const ALLOWED_TABLES = [
  "colaboradores",
  "sucursales",
  "traslados",
  "licencias",
  "vacaciones",
  "usuarios",
  "auditoria",
];

function corsHeaders() {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers":
      "authorization, x-client-info, apikey, content-type, accept, origin",
    "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
    "Access-Control-Max-Age": "86400",
    "Content-Type": "application/json",
  };
}

function response(req: Request, data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: corsHeaders(),
  });
}

function camelToSnake(key: string): string {
  return key.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

function snakeToCamel(key: string): string {
  return key.replace(/_([a-z])/g, (_, letter) => letter.toUpperCase());
}

function convertToDb(obj: any): any {
  if (Array.isArray(obj)) return obj.map(convertToDb);
  if (obj && typeof obj === "object") {
    const result: any = {};
    for (const [key, value] of Object.entries(obj)) {
      result[camelToSnake(key)] = convertToDb(value);
    }
    return result;
  }
  return obj;
}

function convertFromDb(obj: any): any {
  if (Array.isArray(obj)) return obj.map(convertFromDb);
  if (obj && typeof obj === "object") {
    const result: any = {};
    for (const [key, value] of Object.entries(obj)) {
      result[snakeToCamel(key)] = convertFromDb(value);
    }
    return result;
  }
  return obj;
}

function base64url(data: Uint8Array): string {
  let binary = "";
  for (const byte of data) binary += String.fromCharCode(byte);
  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function encodeJson(obj: any): string {
  return base64url(new TextEncoder().encode(JSON.stringify(obj)));
}

async function signToken(payload: any): Promise<string> {
  const header = encodeJson({ alg: "HS256", typ: "JWT" });
  const body = encodeJson(payload);
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(JWT_SECRET),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(`${header}.${body}`),
  );
  return `${header}.${body}.${base64url(new Uint8Array(signature))}`;
}

async function verifyToken(token: string): Promise<any | null> {
  try {
    const parts = token.split(".");
    if (parts.length !== 3) return null;

    const [header, body, signature] = parts;

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(JWT_SECRET),
      { name: "HMAC", hash: "SHA-256" },
      false,
      ["verify"],
    );

    const signatureBytes = Uint8Array.from(
      atob(
        signature
          .replace(/-/g, "+")
          .replace(/_/g, "/")
          .padEnd(Math.ceil(signature.length / 4) * 4, "="),
      ),
      c => c.charCodeAt(0),
    );

    const valid = await crypto.subtle.verify(
      "HMAC",
      key,
      signatureBytes,
      new TextEncoder().encode(`${header}.${body}`),
    );

    if (!valid) return null;

    const payload = JSON.parse(
      new TextDecoder().decode(
        Uint8Array.from(
          atob(
            body
              .replace(/-/g, "+")
              .replace(/_/g, "/")
              .padEnd(Math.ceil(body.length / 4) * 4, "="),
          ),
          c => c.charCodeAt(0),
        ),
      ),
    );

    if (!payload.exp || payload.exp < Date.now()) return null;
    return payload;
  } catch {
    return null;
  }
}

function getToken(req: Request): string | null {
  const auth = req.headers.get("Authorization");
  if (!auth || !auth.startsWith("Bearer ")) return null;
  return auth.substring(7);
}

async function requireAuth(req: Request) {
  const token = getToken(req);
  if (!token) return null;

  const payload = await verifyToken(token);
  if (!payload || !payload.sessionId) return null;

  const { data: session, error } = await supabase
    .from("sesiones")
    .select("*")
    .eq("session_id", payload.sessionId)
    .is("revoked_at", null)
    .maybeSingle();

  if (error || !session) return null;

  await supabase
    .from("sesiones")
    .update({ last_activity_at: new Date().toISOString() })
    .eq("session_id", payload.sessionId);

  return payload;
}

async function hashPassword(password: string): Promise<string> {
  const data = new TextEncoder().encode(password);
  const hash = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

function generateSessionId(): string {
  return crypto.randomUUID();
}

async function login(username: string, password: string) {
  const { data: users, error } = await supabase
    .from("usuarios")
    .select("*")
    .eq("username", username.toLowerCase())
    .limit(1);

  if (error) throw error;
  if (!users || users.length === 0) {
    throw new Error("Usuario o contraseña incorrectos");
  }

  const user = users[0];
  const passwordHash = user.password_hash ?? user.passwordHash ?? "";

  if (!user.activo) throw new Error("Usuario inactivo");

  const hash = await hashPassword(password);
  if (hash !== passwordHash) {
    throw new Error("Usuario o contraseña incorrectos");
  }

  const sessionId = generateSessionId();

  const payload = {
    username: user.username,
    role: user.role,
    sucursal: user.sucursal,
    sessionId,
    exp: Date.now() + 12 * 60 * 60 * 1000,
  };

  const token = await signToken(payload);

  const { error: sessionError } = await supabase
    .from("sesiones")
    .insert({
      session_id: sessionId,
      username: user.username,
      role: user.role,
      sucursal: user.sucursal ?? null,
    });

  if (sessionError) {
    console.error("Error creando sesión:", sessionError);
    throw new Error("No fue posible crear la sesión");
  }

  const safeUser = { ...user };
  delete safeUser.password_hash;
  delete safeUser.passwordHash;

  return {
    token,
    user: convertFromDb(safeUser),
  };
}

async function getAllRows(table: string) {
  const PAGE_SIZE = 1000;
  const rows: any[] = [];
  let from = 0;

  while (true) {
    const to = from + PAGE_SIZE - 1;
    const { data, error } = await supabase
      .from(table)
      .select("*")
      .range(from, to);

    if (error) throw error;

    const page = data || [];
    rows.push(...page);

    if (page.length < PAGE_SIZE) break;
    from += PAGE_SIZE;
  }

  return rows;
}

async function getState() {
  const state: any = {};

  for (const table of ALLOWED_TABLES) {
    state[table] = convertFromDb(await getAllRows(table));
  }

  state.usuarios = state.usuarios.map((u: any) => {
    const safe = { ...u };
    delete safe.passwordHash;
    delete safe.password_hash;
    return safe;
  });

  return state;
}

function schemaColumnFromError(error: any): string | null {
  const message = String(error?.message || "");
  const match = message.match(/Could not find the '([^']+)' column/i);
  return match ? match[1] : null;
}

/*
 * Guarda un registro intentando adaptarse al esquema real.
 * Esto es especialmente importante para TRASLADOS porque el
 * frontend puede enviar campos que no existan en una versión
 * anterior de la tabla.
 */
async function upsertWithSchemaFallback(table: string, record: any) {
  let working = { ...record };

  for (let attempt = 0; attempt < 30; attempt++) {
    const { data, error } = await supabase
      .from(table)
      .upsert(working)
      .select();

    if (!error) return data || [];

    const badColumn = schemaColumnFromError(error);

    if (!badColumn) {
      console.error(`Error guardando ${table}:`, error);
      throw new Error(
        `Error guardando ${table}: ${error.message || "Error desconocido"}`
      );
    }

    if (!Object.prototype.hasOwnProperty.call(working, badColumn)) {
      throw new Error(
        `La columna ${badColumn} no existe en ${table} y no fue posible adaptar el registro.`
      );
    }

    delete working[badColumn];

    console.warn(
      `Se omitirá la columna inexistente ${badColumn} de ${table} y se reintentará.`,
    );
  }

  throw new Error(
    `No fue posible guardar ${table}: demasiadas diferencias de esquema.`,
  );
}

async function upsertRecord(table: string, record: any) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  if (!record || typeof record !== "object") {
    throw new Error("Registro inválido");
  }

  /*
   * USUARIOS
   */
  if (table === "usuarios") {
    const dbRecord = convertToDb(record);

    delete dbRecord.id;

    if (dbRecord.username !== undefined && dbRecord.username !== null) {
      dbRecord.username = String(dbRecord.username).trim().toLowerCase();
    }

    if (!dbRecord.username) {
      throw new Error("El nombre de usuario es obligatorio");
    }

    if (!dbRecord.password_hash) {
      throw new Error("La contraseña es obligatoria");
    }

    if (dbRecord.last_login === "" || dbRecord.last_login === undefined) {
      dbRecord.last_login = null;
    }

    if (dbRecord.created_at === "") {
      dbRecord.created_at = null;
    }

    const { data: existing, error: findError } = await supabase
      .from("usuarios")
      .select("*")
      .eq("username", dbRecord.username)
      .limit(1);

    if (findError) {
      throw new Error(
        `Error buscando usuario: ${findError.message || "Error desconocido"}`
      );
    }

    if (existing && existing.length > 0) {
      delete dbRecord.created_at;

      const { data, error } = await supabase
        .from("usuarios")
        .update(dbRecord)
        .eq("username", dbRecord.username)
        .select();

      if (error) {
        throw new Error(
          `Error actualizando usuario: ${error.message || "Error desconocido"}`
        );
      }

      return convertFromDb(data || []);
    }

    if (dbRecord.created_at === null || dbRecord.created_at === undefined) {
      dbRecord.created_at = new Date().toISOString();
    }

    const { data, error } = await supabase
      .from("usuarios")
      .insert(dbRecord)
      .select();

    if (error) {
      throw new Error(
        `Error creando usuario: ${error.message || "Error desconocido"}`
      );
    }

    return convertFromDb(data || []);
  }

  /*
   * TRASLADOS
   *
   * El frontend actual genera:
   * id, rut, colaboradorNombre, origen, destino,
   * fechaSolicitud, fechaInicio, fechaTermino,
   * indefinido, fechaEfectiva, motivo,
   * solicitadoPor, estado, createdAt.
   */
  if (table === "traslados") {
    const allowedFields = [
      "id",
      "rut",
      "nombre",
      "colaboradorNombre",
      "origen",
      "destino",
      "fechaSolicitud",
      "fechaInicio",
      "fechaTermino",
      "fechaEfectiva",
      "indefinido",
      "estado",
      "motivo",
      "observaciones",
      "solicitadoPor",
      "createdAt",
      "updatedAt",
    ];

    const clean: any = {};

    for (const field of allowedFields) {
      if (Object.prototype.hasOwnProperty.call(record, field)) {
        if (record[field] !== undefined) {
          clean[field] = record[field];
        }
      }
    }

    if (!clean.colaboradorNombre && clean.nombre) {
      clean.colaboradorNombre = clean.nombre;
    }

    if (!clean.nombre && clean.colaboradorNombre) {
      clean.nombre = clean.colaboradorNombre;
    }

    if (clean.fechaTermino === "") {
      clean.fechaTermino = null;
    }

    if (clean.indefinido === true) {
      clean.fechaTermino = null;
    }

    const dbRecord = convertToDb(clean);
    const data = await upsertWithSchemaFallback("traslados", dbRecord);

    return convertFromDb(data);
  }

  /*
   * RESTO DE TABLAS
   */
  const dbRecord = convertToDb(record);
  const data = await upsertWithSchemaFallback(table, dbRecord);

  return convertFromDb(data);
}

async function bulkUpsert(table: string, records: any[]) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  if (!Array.isArray(records)) {
    throw new Error("Los registros deben ser un arreglo");
  }

  if (records.length === 0) return [];

  const TABLE_FIELDS: Record<string, string[]> = {
    colaboradores: [
      "id", "rut", "nombre", "cargo", "sucursalActual", "area",
      "fechaIngreso", "email", "telefono", "estado",
    ],

    sucursales: [
      "id", "codigo", "nombre", "region", "comuna", "direccion", "encargado",
    ],

    traslados: [
      "id", "rut", "nombre", "colaboradorNombre",
      "origen", "destino", "fechaSolicitud",
      "fechaInicio", "fechaTermino", "fechaEfectiva",
      "indefinido", "estado", "motivo", "observaciones",
      "solicitadoPor", "createdAt", "updatedAt",
    ],

    vacaciones: [
      "id", "rut", "nombreColaborador", "nombre", "cargo", "sucursal",
      "tipoAusencia", "tipo", "numeroDias", "dias",
      "fechaInicio", "inicio", "fechaTermino", "termino", "estado",
    ],

    licencias: [
      "id", "rut", "nombreColaborador", "nombre", "cargo", "sucursal",
      "tipoAusencia", "tipo", "numeroDias", "dias",
      "fechaInicio", "inicio", "fechaTermino", "termino", "estado",
    ],

    usuarios: [
      "id", "username", "nombre", "passwordHash", "role",
      "sucursal", "activo", "createdAt", "lastLogin",
    ],

    auditoria: [
      "id", "fecha", "usuario", "tipo", "accion", "elemento", "detalle",
    ],
  };

  const allowedFields = TABLE_FIELDS[table];

  if (!allowedFields) {
    throw new Error(
      `No existe configuración de campos para la tabla ${table}`,
    );
  }

  const cleanRecords = records.map((record: any) => {
    if (!record || typeof record !== "object") {
      throw new Error("Registro inválido");
    }

    const clean: any = {};

    for (const field of allowedFields) {
      if (Object.prototype.hasOwnProperty.call(record, field)) {
        if (record[field] !== undefined) {
          clean[field] = record[field];
        }
      }
    }

    if (table === "traslados") {
      if (!clean.colaboradorNombre && clean.nombre) {
        clean.colaboradorNombre = clean.nombre;
      }
      if (!clean.nombre && clean.colaboradorNombre) {
        clean.nombre = clean.colaboradorNombre;
      }
      if (clean.fechaTermino === "") {
        clean.fechaTermino = null;
      }
      if (clean.indefinido === true) {
        clean.fechaTermino = null;
      }
    }

    if (table === "vacaciones" || table === "licencias") {
      if (!clean.nombre && clean.nombreColaborador) {
        clean.nombre = clean.nombreColaborador;
      }
      if (!clean.nombreColaborador && clean.nombre) {
        clean.nombreColaborador = clean.nombre;
      }
      if (clean.tipo === undefined && clean.tipoAusencia !== undefined) {
        clean.tipo = clean.tipoAusencia;
      }
      if (clean.tipoAusencia === undefined && clean.tipo !== undefined) {
        clean.tipoAusencia = clean.tipo;
      }
      if (clean.dias === undefined && clean.numeroDias !== undefined) {
        clean.dias = clean.numeroDias;
      }
      if (clean.numeroDias === undefined && clean.dias !== undefined) {
        clean.numeroDias = clean.dias;
      }
      if (clean.inicio === undefined && clean.fechaInicio !== undefined) {
        clean.inicio = clean.fechaInicio;
      }
      if (clean.fechaInicio === undefined && clean.inicio !== undefined) {
        clean.fechaInicio = clean.inicio;
      }
      if (clean.termino === undefined && clean.fechaTermino !== undefined) {
        clean.termino = clean.fechaTermino;
      }
      if (clean.fechaTermino === undefined && clean.termino !== undefined) {
        clean.fechaTermino = clean.termino;
      }
      if (clean.fechaTermino === "") clean.fechaTermino = null;
      if (clean.termino === "") clean.termino = null;
    }

    return convertToDb(clean);
  });

  const CHUNK_SIZE = 100;
  const saved: any[] = [];

  for (let i = 0; i < cleanRecords.length; i += CHUNK_SIZE) {
    const chunk = cleanRecords.slice(i, i + CHUNK_SIZE);

    let working = chunk.map(row => ({ ...row }));

    for (let attempt = 0; attempt < 30; attempt++) {
      const { data, error } = await supabase
        .from(table)
        .upsert(working)
        .select();

      if (!error) {
        saved.push(...(data || []));
        break;
      }

      const badColumn = schemaColumnFromError(error);

      if (!badColumn) {
        throw new Error(
          `Error guardando ${table}: ${error.message || "Error desconocido"}`
        );
      }

      let removed = false;

      working = working.map(row => {
        if (Object.prototype.hasOwnProperty.call(row, badColumn)) {
          const copy = { ...row };
          delete copy[badColumn];
          removed = true;
          return copy;
        }
        return row;
      });

      if (!removed) {
        throw new Error(
          `Error guardando ${table}: ${error.message || "Esquema incompatible"}`
        );
      }
    }
  }

  return convertFromDb(saved);
}

async function deleteRecord(table: string, id: any, record: any = null) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  if (table === "usuarios") {
    throw new Error("No se permite eliminar usuarios desde esta función");
  }

  /*
   * Acepta tanto {id} como {record:{id}} y, para las funciones
   * antiguas del frontend, también criterios como rut/codigo.
   */
  const criteria: any = record && typeof record === "object"
    ? record
    : (id && typeof id === "object" ? id : { id });

  const clean: any = {};
  for (const [key, value] of Object.entries(criteria)) {
    if (value !== undefined && value !== null && value !== "") {
      clean[key] = value;
    }
  }

  if (!Object.keys(clean).length) {
    throw new Error("Criterio requerido para eliminar");
  }

  let query = supabase.from(table).delete();

  for (const [key, value] of Object.entries(clean)) {
    query = query.eq(camelToSnake(key), value);
  }

  const { error } = await query;

  if (error) throw error;

  return true;
}

async function clearTable(table: string) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  if (table === "usuarios") {
    throw new Error("No se permite limpiar la tabla usuarios");
  }

  const { data, error } = await supabase
    .from(table)
    .select("id");

  if (error) throw error;
  if (!data || data.length === 0) return true;

  const ids = data
    .map((row: any) => row.id)
    .filter((id: any) => id !== null && id !== undefined);

  if (ids.length === 0) return true;

  const { error: deleteError } = await supabase
    .from(table)
    .delete()
    .in("id", ids);

  if (deleteError) throw deleteError;

  return true;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: corsHeaders(),
    });
  }

  if (
    req.method === "GET" &&
    new URL(req.url).pathname.endsWith("/health")
  ) {
    return response(req, {
      ok: true,
      service: "panel-api",
      version: "2026-09-21-session-management-v2",
    });
  }

  try {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "");

    /*
     * LOGIN
     */
    if (req.method === "POST") {
      const probe = req.clone();
      let probeBody: any = null;

      try {
        probeBody = await probe.json();
      } catch {
        probeBody = null;
      }

      const isLoginRequest =
        !!probeBody &&
        typeof probeBody === "object" &&
        typeof probeBody.username === "string" &&
        typeof probeBody.password === "string" &&
        !probeBody.action;

      if (isLoginRequest) {
        if (!probeBody.username || !probeBody.password) {
          return response(
            req,
            { error: "Usuario y contraseña son obligatorios" },
            400,
          );
        }

        try {
          const result = await login(
            String(probeBody.username).trim(),
            String(probeBody.password),
          );

          return response(req, result, 200);
        } catch (error) {
          console.error("Error login:", error);

          return response(
            req,
            {
              error:
                error instanceof Error
                  ? error.message
                  : "Error de autenticación",
            },
            401,
          );
        }
      }
    }

    /*
     * AUTENTICACIÓN
     */
    const auth = await requireAuth(req);

    if (!auth) {
      return response(
        req,
        { error: "Sesión no válida o expirada" },
        401,
      );
    }

    /*
     * SESIONES ACTIVAS
     */
    if (req.method === "GET" && path.endsWith("/sessions")) {
      if (auth.role !== "superadmin") {
        return response(
          req,
          { error: "Se requiere Super Admin" },
          403,
        );
      }

      const { data, error } = await supabase
        .from("sesiones")
        .select(
          "id, session_id, username, role, sucursal, created_at, last_activity_at, revoked_at",
        )
        .is("revoked_at", null)
        .order("last_activity_at", { ascending: false });

      if (error) throw error;

      return response(req, {
        success: true,
        sessions: data || [],
      });
    }

    /*
     * STATE
     */
    if (req.method === "GET" && path.endsWith("/state")) {
      const state = await getState();

      return response(
        req,
        {
          state,
          user: auth,
        },
        200,
      );
    }

    /*
     * POST ACTIONS
     */
    if (req.method === "POST") {
      const body = await req.json();

      /*
       * REVOCAR SESIÓN
       */
      if (body.action === "revokeSession") {
        if (auth.role !== "superadmin") {
          return response(
            req,
            { error: "Se requiere Super Admin" },
            403,
          );
        }

        const sessionId = String(body.sessionId || "").trim();

        if (!sessionId) {
          return response(
            req,
            { error: "sessionId requerido" },
            400,
          );
        }

        if (sessionId === auth.sessionId) {
          return response(
            req,
            { error: "No puedes cerrar tu propia sesión" },
            400,
          );
        }

        const {
          data: targetSession,
          error: findError,
        } = await supabase
          .from("sesiones")
          .select("*")
          .eq("session_id", sessionId)
          .maybeSingle();

        if (findError) throw findError;

        if (!targetSession) {
          return response(
            req,
            { error: "Sesión no encontrada" },
            404,
          );
        }

        const { error: revokeError } = await supabase
          .from("sesiones")
          .update({
            revoked_at: new Date().toISOString(),
          })
          .eq("session_id", sessionId);

        if (revokeError) throw revokeError;

        return response(req, {
          success: true,
          message: "Sesión cerrada correctamente",
        });
      }

      /*
       * CERRAR TODAS LAS DEMÁS SESIONES
       */
      if (body.action === "revokeAllSessions") {
        if (auth.role !== "superadmin") {
          return response(
            req,
            { error: "Se requiere Super Admin" },
            403,
          );
        }

        const { error } = await supabase
          .from("sesiones")
          .update({
            revoked_at: new Date().toISOString(),
          })
          .is("revoked_at", null)
          .neq("session_id", auth.sessionId);

        if (error) throw error;

        return response(req, {
          success: true,
          message: "Todas las demás sesiones fueron cerradas",
        });
      }

      /*
       * UPSERT
       */
      if (body.action === "upsert") {
        const result = await upsertRecord(
          body.table,
          body.record,
        );

        return response(req, {
          success: true,
          data: result,
        });
      }

      /*
       * BULK UPSERT
       */
      if (body.action === "bulkUpsert") {
        const result = await bulkUpsert(
          body.table,
          body.records || [],
        );

        return response(req, {
          success: true,
          data: result,
        });
      }

      /*
       * DELETE
       */
      if (body.action === "delete") {
        const result = await deleteRecord(
          body.table,
          body.id,
          body.record,
        );

        return response(req, {
          success: result,
        });
      }

      /*
       * CLEAR
       */
      if (body.action === "clear") {
        if (auth.role !== "superadmin") {
          return response(
            req,
            { error: "Se requiere Super Admin" },
            403,
          );
        }

        await clearTable(body.table);

        return response(req, {
          success: true,
        });
      }
    }

    return response(
      req,
      { error: "Ruta o acción no válida" },
      404,
    );
  } catch (error) {
    console.error("Error interno:", error);

    return response(
      req,
      {
        error:
          error instanceof Error
            ? error.message
            : "Error interno del servidor",
      },
      500,
    );
  }
});
