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
    "Access-Control-Allow-Methods":
      "GET, POST, DELETE, OPTIONS",
    "Access-Control-Max-Age": "86400",
    "Content-Type": "application/json",
  };
}

function response(
  req: Request,
  data: unknown,
  status = 200,
) {
  return new Response(JSON.stringify(data), {
    status,
    headers: corsHeaders(),
  });
}

function camelToSnake(key: string): string {
  return key.replace(
    /[A-Z]/g,
    letter => `_${letter.toLowerCase()}`
  );
}

function snakeToCamel(key: string): string {
  return key.replace(
    /_([a-z])/g,
    (_, letter) => letter.toUpperCase()
  );
}

function convertToDb(obj: any): any {
  if (Array.isArray(obj)) {
    return obj.map(convertToDb);
  }

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
  if (Array.isArray(obj)) {
    return obj.map(convertFromDb);
  }

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

  for (const byte of data) {
    binary += String.fromCharCode(byte);
  }

  return btoa(binary)
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function encodeJson(obj: any): string {
  return base64url(
    new TextEncoder().encode(JSON.stringify(obj))
  );
}

async function signToken(payload: any): Promise<string> {
  const header = encodeJson({
    alg: "HS256",
    typ: "JWT",
  });

  const body = encodeJson(payload);

  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(JWT_SECRET),
    {
      name: "HMAC",
      hash: "SHA-256",
    },
    false,
    ["sign"],
  );

  const signature = await crypto.subtle.sign(
    "HMAC",
    key,
    new TextEncoder().encode(`${header}.${body}`),
  );

  return `${header}.${body}.${base64url(
    new Uint8Array(signature)
  )}`;
}

async function verifyToken(
  token: string
): Promise<any | null> {
  try {
    const parts = token.split(".");

    if (parts.length !== 3) {
      return null;
    }

    const [header, body, signature] = parts;

    const key = await crypto.subtle.importKey(
      "raw",
      new TextEncoder().encode(JWT_SECRET),
      {
        name: "HMAC",
        hash: "SHA-256",
      },
      false,
      ["verify"],
    );

    const signatureBytes = Uint8Array.from(
      atob(
        signature
          .replace(/-/g, "+")
          .replace(/_/g, "/")
          .padEnd(
            Math.ceil(signature.length / 4) * 4,
            "="
          )
      ),
      c => c.charCodeAt(0)
    );

    const valid = await crypto.subtle.verify(
      "HMAC",
      key,
      signatureBytes,
      new TextEncoder().encode(`${header}.${body}`),
    );

    if (!valid) {
      return null;
    }

    const payload = JSON.parse(
      new TextDecoder().decode(
        Uint8Array.from(
          atob(
            body
              .replace(/-/g, "+")
              .replace(/_/g, "/")
              .padEnd(
                Math.ceil(body.length / 4) * 4,
                "="
              )
          ),
          c => c.charCodeAt(0)
        )
      )
    );

    if (!payload.exp) {
      return null;
    }

    if (payload.exp < Date.now()) {
      return null;
    }

    return payload;
  } catch {
    return null;
  }
}

function getToken(req: Request): string | null {
  const auth = req.headers.get("Authorization");

  if (!auth) {
    return null;
  }

  if (!auth.startsWith("Bearer ")) {
    return null;
  }

  return auth.substring(7);
}

async function requireAuth(req: Request) {
  const token = getToken(req);

  if (!token) {
    return null;
  }

  return await verifyToken(token);
}

async function hashPassword(
  password: string
): Promise<string> {
  const data = new TextEncoder().encode(password);

  const hash = await crypto.subtle.digest(
    "SHA-256",
    data
  );

  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
}

async function login(
  username: string,
  password: string
) {
  const { data: users, error } = await supabase
    .from("usuarios")
    .select("*")
    .eq("username", username.toLowerCase())
    .limit(1);

  if (error) {
    throw error;
  }

  if (!users || users.length === 0) {
    throw new Error(
      "Usuario o contraseña incorrectos"
    );
  }

  const user = users[0];

  const passwordHash =
    user.password_hash ??
    user.passwordHash ??
    "";

  if (!user.activo) {
    throw new Error("Usuario inactivo");
  }

  const hash = await hashPassword(password);

  if (hash !== passwordHash) {
    throw new Error(
      "Usuario o contraseña incorrectos"
    );
  }

  const payload = {
    username: user.username,
    role: user.role,
    sucursal: user.sucursal,
    exp: Date.now() + 12 * 60 * 60 * 1000,
  };

  const token = await signToken(payload);

  const safeUser = { ...user };

  delete safeUser.password_hash;
  delete safeUser.passwordHash;

  return {
    token,
    user: convertFromDb(safeUser),
  };
}

const API_PAGE_SIZE = 1000;

async function getAllRows(table: string) {
  const all: any[] = [];
  let from = 0;

  while (true) {
    const { data, error } = await supabase
      .from(table)
      .select("*")
      .range(from, from + API_PAGE_SIZE - 1);

    if (error) {
      console.error(
        `Error leyendo ${table} desde ${from}:`,
        error
      );
      throw error;
    }

    const rows = data || [];
    all.push(...rows);

    if (rows.length < API_PAGE_SIZE) {
      break;
    }

    from += API_PAGE_SIZE;
  }

  return all;
}

async function deleteAllRows(table: string) {
  let deletedTotal = 0;

  while (true) {
    const { data, error } = await supabase
      .from(table)
      .select("id")
      .range(0, API_PAGE_SIZE - 1);

    if (error) {
      throw error;
    }

    const ids = (data || [])
      .map((row: any) => row.id)
      .filter(
        (id: any) =>
          id !== null &&
          id !== undefined
      );

    if (ids.length === 0) {
      break;
    }

    const { error: deleteError } = await supabase
      .from(table)
      .delete()
      .in("id", ids);

    if (deleteError) {
      throw deleteError;
    }

    deletedTotal += ids.length;

    if (ids.length < API_PAGE_SIZE) {
      break;
    }
  }

  return deletedTotal;
}

async function getState() {
  const state: any = {};

  for (const table of ALLOWED_TABLES) {
    const data = await getAllRows(table);
    state[table] = convertFromDb(data || []);
  }

  state.usuarios = state.usuarios.map(
    (u: any) => {
      const safe = { ...u };

      delete safe.passwordHash;
      delete safe.password_hash;

      return safe;
    }
  );

  return state;
}


/* =========================================================
   UPSERT
   ========================================================= */

async function upsertRecord(
  table: string,
  record: any
) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  const dbRecord = convertToDb(record);

  /*
   * USUARIOS
   *
   * No usamos upsert directamente porque depende de que
   * Supabase tenga correctamente configurado el índice/clave
   * única de username.
   *
   * Primero buscamos el usuario.
   * Si existe -> UPDATE
   * Si no existe -> INSERT
   */

  if (table === "usuarios") {
    const username = String(
      dbRecord.username || ""
    )
      .trim()
      .toLowerCase();

    if (!username) {
      throw new Error(
        "El usuario es obligatorio"
      );
    }

    dbRecord.username = username;

    const {
      data: existing,
      error: findError,
    } = await supabase
      .from("usuarios")
      .select("*")
      .eq("username", username)
      .limit(1);

    if (findError) {
      throw new Error(
        `No se pudo consultar el usuario: ${
          findError.message ||
          "error de base de datos"
        }`
      );
    }

    let result;

    /*
     * USUARIO YA EXISTENTE
     */

    if (
      existing &&
      existing.length > 0
    ) {
      const current = existing[0];

      const key =
        current.id !== undefined &&
        current.id !== null
          ? {
              column: "id",
              value: current.id,
            }
          : {
              column: "username",
              value: username,
            };

      const {
        data,
        error,
      } = await supabase
        .from("usuarios")
        .update(dbRecord)
        .eq(
          key.column,
          key.value
        )
        .select();

      if (error) {
        throw new Error(
          `No se pudo actualizar el usuario: ${
            error.message ||
            "error de base de datos"
          }`
        );
      }

      result = data || [];
    }

    /*
     * USUARIO NUEVO
     */

    else {
      const {
        data,
        error,
      } = await supabase
        .from("usuarios")
        .insert(dbRecord)
        .select();

      if (error) {
        throw new Error(
          `No se pudo crear el usuario: ${
            error.message ||
            "error de base de datos"
          }`
        );
      }

      result = data || [];
    }

    return convertFromDb(result);
  }

  /*
   * RESTO DE LAS TABLAS
   */

  const {
    data,
    error,
  } = await supabase
    .from(table)
    .upsert(dbRecord)
    .select();

  if (error) {
    throw error;
  }

  return convertFromDb(data || []);
}


/* =========================================================
   BULK UPSERT
   ========================================================= */

async function bulkUpsert(
  table: string,
  records: any[]
) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error(
      "Tabla no permitida"
    );
  }

  if (!Array.isArray(records)) {
    throw new Error(
      "Los registros deben ser un arreglo"
    );
  }

  if (records.length === 0) {
    return [];
  }

  const TABLE_FIELDS: Record<
    string,
    string[]
  > = {

    colaboradores: [
      "id",
      "rut",
      "nombre",
      "cargo",
      "sucursalActual",
      "area",
      "fechaIngreso",
      "email",
      "telefono",
      "estado",
    ],

    sucursales: [
      "id",
      "codigo",
      "nombre",
      "region",
      "comuna",
      "direccion",
      "encargado",
    ],

    traslados: [
      "id",
      "rut",
      "nombre",
      "colaboradorNombre",
      "origen",
      "destino",
      "fechaInicio",
      "fechaTermino",
      "indefinido",
      "estado",
      "motivo",
      "observaciones",
      "createdAt",
      "updatedAt",
    ],

    vacaciones: [
      "id",
      "rut",
      "nombreColaborador",
      "nombre",
      "cargo",
      "sucursal",
      "tipoAusencia",
      "tipo",
      "numeroDias",
      "dias",
      "fechaInicio",
      "inicio",
      "fechaTermino",
      "termino",
      "estado",
    ],

    licencias: [
      "id",
      "rut",
      "nombreColaborador",
      "nombre",
      "cargo",
      "sucursal",
      "tipoAusencia",
      "tipo",
      "numeroDias",
      "dias",
      "fechaInicio",
      "inicio",
      "fechaTermino",
      "termino",
      "estado",
    ],

    usuarios: [
      "id",
      "username",
      "nombre",
      "passwordHash",
      "role",
      "sucursal",
      "activo",
      "createdAt",
      "lastLogin",
    ],

    auditoria: [
      "id",
      "fecha",
      "usuario",
      "tipo",
      "accion",
      "elemento",
      "detalle",
    ],
  };

  const allowedFields =
    TABLE_FIELDS[table];

  if (!allowedFields) {
    throw new Error(
      `No existe configuración de campos para la tabla ${table}`
    );
  }

  const cleanRecords =
    records.map((record: any) => {

      if (
        !record ||
        typeof record !== "object"
      ) {
        throw new Error(
          "Registro inválido"
        );
      }

      const clean: any = {};

      for (
        const field of allowedFields
      ) {
        if (
          Object.prototype.hasOwnProperty.call(
            record,
            field
          )
        ) {
          const value =
            record[field];

          if (
            value !== undefined
          ) {
            clean[field] =
              value;
          }
        }
      }

      /*
       * VACACIONES / LICENCIAS
       */

      if (
        table === "vacaciones" ||
        table === "licencias"
      ) {

        if (
          !clean.nombre &&
          clean.nombreColaborador
        ) {
          clean.nombre =
            clean.nombreColaborador;
        }

        if (
          !clean.nombreColaborador &&
          clean.nombre
        ) {
          clean.nombreColaborador =
            clean.nombre;
        }

        if (
          clean.tipo === undefined &&
          clean.tipoAusencia !== undefined
        ) {
          clean.tipo =
            clean.tipoAusencia;
        }

        if (
          clean.tipoAusencia === undefined &&
          clean.tipo !== undefined
        ) {
          clean.tipoAusencia =
            clean.tipo;
        }

        if (
          clean.dias === undefined &&
          clean.numeroDias !== undefined
        ) {
          clean.dias =
            clean.numeroDias;
        }

        if (
          clean.numeroDias === undefined &&
          clean.dias !== undefined
        ) {
          clean.numeroDias =
            clean.dias;
        }

        if (
          clean.inicio === undefined &&
          clean.fechaInicio !== undefined
        ) {
          clean.inicio =
            clean.fechaInicio;
        }

        if (
          clean.fechaInicio === undefined &&
          clean.inicio !== undefined
        ) {
          clean.fechaInicio =
            clean.inicio;
        }

        if (
          clean.termino === undefined &&
          clean.fechaTermino !== undefined
        ) {
          clean.termino =
            clean.fechaTermino;
        }

        if (
          clean.fechaTermino === undefined &&
          clean.termino !== undefined
        ) {
          clean.fechaTermino =
            clean.termino;
        }

        if (
          clean.fechaTermino === ""
        ) {
          clean.fechaTermino = null;
        }

        if (
          clean.termino === ""
        ) {
          clean.termino = null;
        }
      }

      return convertToDb(clean);
    });


  function schemaColumnFromError(
    error: any
  ): string | null {

    const message =
      String(
        error?.message || ""
      );

    const match =
      message.match(
        /Could not find the '([^']+)' column/i
      );

    return match
      ? match[1]
      : null;
  }


  async function upsertChunkWithSchemaFallback(
    chunk: any[]
  ) {

    let working =
      chunk.map(
        row => ({
          ...row
        })
      );

    for (
      let attempt = 0;
      attempt < 25;
      attempt++
    ) {

      const {
        data,
        error
      } = await supabase
        .from(table)
        .upsert(working)
        .select();

      if (!error) {
        return data || [];
      }

      const badColumn =
        schemaColumnFromError(
          error
        );

      if (!badColumn) {

        console.error(
          `Error guardando masivamente ${table}:`,
          error
        );

        throw new Error(
          `Error guardando ${table}: ${
            error.message ||
            "Error desconocido"
          }`
        );
      }

      let removed = false;

      working =
        working.map(
          (row) => {

            if (
              Object.prototype.hasOwnProperty.call(
                row,
                badColumn
              )
            ) {

              const copy = {
                ...row
              };

              delete copy[
                badColumn
              ];

              removed = true;

              return copy;
            }

            return row;
          }
        );

      if (!removed) {

        console.error(
          `PostgREST rechazó una columna que no estaba en el payload de ${table}:`,
          badColumn,
          error
        );

        throw new Error(
          `Error guardando ${table}: ${
            error.message ||
            "Esquema incompatible"
          }`
        );
      }

      console.warn(
        `Se omitirá la columna inexistente ${badColumn} de ${table} y se reintentará la importación.`
      );
    }

    throw new Error(
      `No fue posible guardar ${table}: demasiadas diferencias de esquema.`
    );
  }


  /*
   * Archivos grandes se guardan en bloques.
   */

  const CHUNK_SIZE = 100;

  const saved: any[] = [];

  for (
    let i = 0;
    i < cleanRecords.length;
    i += CHUNK_SIZE
  ) {

    const chunk =
      cleanRecords.slice(
        i,
        i + CHUNK_SIZE
      );

    const data =
      await upsertChunkWithSchemaFallback(
        chunk
      );

    saved.push(
      ...data
    );
  }

  return convertFromDb(
    saved
  );
}


/* =========================================================
   DELETE
   ========================================================= */

async function deleteRecord(
  table: string,
  id: any
) {

  if (
    !ALLOWED_TABLES.includes(table)
  ) {
    throw new Error(
      "Tabla no permitida"
    );
  }

  if (table === "usuarios") {
    throw new Error(
      "No se permite eliminar usuarios desde esta función"
    );
  }

  if (
    id === undefined ||
    id === null
  ) {
    throw new Error(
      "ID requerido para eliminar"
    );
  }

  const {
    error
  } = await supabase
    .from(table)
    .delete()
    .eq("id", id);

  if (error) {
    throw error;
  }

  return true;
}


/* =========================================================
   CLEAR TABLE
   ========================================================= */

async function clearTable(
  table: string
) {

  if (
    !ALLOWED_TABLES.includes(table)
  ) {
    throw new Error(
      "Tabla no permitida"
    );
  }

  if (table === "usuarios") {
    throw new Error(
      "No se permite limpiar la tabla usuarios"
    );
  }

  await deleteAllRows(
    table
  );

  return true;
}


/* =========================================================
   SERVER
   ========================================================= */

Deno.serve(
  async (req: Request) => {

    /*
     * CORS / PREFLIGHT
     */

    if (
      req.method === "OPTIONS"
    ) {

      return new Response(
        null,
        {
          status: 204,
          headers:
            corsHeaders(),
        }
      );
    }

    try {

      const url =
        new URL(req.url);

      const path =
        url.pathname.replace(
          /\/+$/,
          ""
        );


      /* =====================================================
         LOGIN
         ===================================================== */

      if (
        req.method === "POST" &&
        path.endsWith("/login")
      ) {

        let body: any;

        try {

          body =
            await req.json();

        } catch {

          return response(
            req,
            {
              error:
                "Solicitud JSON inválida",
            },
            400
          );
        }

        if (
          !body.username ||
          !body.password
        ) {

          return response(
            req,
            {
              error:
                "Usuario y contraseña son obligatorios",
            },
            400
          );
        }

        try {

          const result =
            await login(
              String(
                body.username
              ),
              String(
                body.password
              )
            );

          return response(
            req,
            result,
            200
          );

        } catch (error) {

          console.error(
            "Error login:",
            error
          );

          return response(
            req,
            {
              error:
                error instanceof Error
                  ? error.message
                  : "Error de autenticación",
            },
            401
          );
        }
      }


      /* =====================================================
         AUTENTICACIÓN
         ===================================================== */

      const auth =
        await requireAuth(
          req
        );

      if (!auth) {

        return response(
          req,
          {
            error:
              "Sesión no válida o expirada",
          },
          401
        );
      }


      /* =====================================================
         STATE
         ===================================================== */

      if (
        req.method === "GET" &&
        path.endsWith("/state")
      ) {

        const state =
          await getState();

        return response(
          req,
          {
            state,
            user: auth,
          },
          200
        );
      }


      /* =====================================================
         POST
         ===================================================== */

      if (
        req.method === "POST"
      ) {

        const body =
          await req.json();


        /* ---------------------------------------------------
           UPSERT
           --------------------------------------------------- */

        if (
          body.action ===
          "upsert"
        ) {

          const result =
            await upsertRecord(
              body.table,
              body.record
            );

          return response(
            req,
            {
              success: true,
              data: result,
            }
          );
        }


        /* ---------------------------------------------------
           BULK UPSERT
           --------------------------------------------------- */

        if (
          body.action ===
          "bulkUpsert"
        ) {

          const result =
            await bulkUpsert(
              body.table,
              body.records ||
                []
            );

          return response(
            req,
            {
              success: true,
              data: result,
            }
          );
        }


        /* ---------------------------------------------------
           DELETE
           --------------------------------------------------- */

        if (
          body.action ===
          "delete"
        ) {

          const result =
            await deleteRecord(
              body.table,
              body.id
            );

          return response(
            req,
            {
              success: result,
            }
          );
        }


        /* ---------------------------------------------------
           CLEAR
           --------------------------------------------------- */

        if (
          body.action ===
          "clear"
        ) {

          if (
            auth.role !==
            "superadmin"
          ) {

            return response(
              req,
              {
                error:
                  "Se requiere Super Admin",
              },
              403
            );
          }

          await clearTable(
            body.table
          );

          return response(
            req,
            {
              success: true,
            }
          );
        }
      }


      return response(
        req,
        {
          error:
            "Ruta o acción no válida",
        },
        404
      );

    } catch (error) {

      console.error(
        "Error interno:",
        error
      );

      /*
       * IMPORTANTE:
       * Ahora mostramos el error REAL de Supabase.
       */

      const errorMessage =
        error instanceof Error
          ? error.message
          : String(
              (error as any)
                ?.message ||
              (error as any)
                ?.details ||
              (error as any)
                ?.hint ||
              error ||
              "Error interno del servidor"
            );

      return response(
        req,
        {
          error:
            errorMessage,
        },
        500
      );
    }
  }
);
