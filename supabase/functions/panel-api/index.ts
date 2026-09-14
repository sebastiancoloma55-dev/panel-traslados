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

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Content-Type": "application/json",
};

function response(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: corsHeaders,
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
          .padEnd(Math.ceil(signature.length / 4) * 4, "=")
      ),
      c => c.charCodeAt(0)
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
              .padEnd(Math.ceil(body.length / 4) * 4, "=")
          ),
          c => c.charCodeAt(0)
        )
      )
    );

    if (!payload.exp || payload.exp < Date.now()) return null;

    return payload;
  } catch {
    return null;
  }
}

function getToken(req: Request): string | null {
  const auth = req.headers.get("Authorization");

  if (!auth) return null;

  if (!auth.startsWith("Bearer ")) return null;

  return auth.substring(7);
}

async function requireAuth(req: Request) {
  const token = getToken(req);

  if (!token) return null;

  return await verifyToken(token);
}

async function hashPassword(password: string): Promise<string> {
  const data = new TextEncoder().encode(password);

  const hash = await crypto.subtle.digest("SHA-256", data);

  return Array.from(new Uint8Array(hash))
    .map(b => b.toString(16).padStart(2, "0"))
    .join("");
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

  const passwordHash =
    user.password_hash ??
    user.passwordHash ??
    "";

  if (!user.activo) {
    throw new Error("Usuario inactivo");
  }

  const hash = await hashPassword(password);

  if (hash !== passwordHash) {
    throw new Error("Usuario o contraseña incorrectos");
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

async function getState() {
  const state: any = {};

  for (const table of ALLOWED_TABLES) {
    const { data, error } = await supabase
      .from(table)
      .select("*");

    if (error) {
      console.error(`Error leyendo ${table}:`, error);
      throw error;
    }

    state[table] = convertFromDb(data || []);
  }

  state.usuarios = state.usuarios.map((u: any) => {
    const safe = { ...u };
    delete safe.passwordHash;
    delete safe.password_hash;
    return safe;
  });

  return state;
}

async function upsertRecord(table: string, record: any) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  const dbRecord = convertToDb(record);

  const { data, error } = await supabase
    .from(table)
    .upsert(dbRecord)
    .select();

  if (error) throw error;

  return convertFromDb(data || []);
}

async function bulkUpsert(table: string, records: any[]) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  const dbRecords = records.map(convertToDb);

  if (dbRecords.length === 0) {
    return [];
  }

  const { data, error } = await supabase
    .from(table)
    .upsert(dbRecords)
    .select();

  if (error) throw error;

  return convertFromDb(data || []);
}

async function clearTable(table: string) {
  if (!ALLOWED_TABLES.includes(table)) {
    throw new Error("Tabla no permitida");
  }

  if (table === "usuarios") {
    throw new Error("No se permite limpiar la tabla usuarios");
  }

  const { error } = await supabase
    .from(table)
    .delete()
    .not("id", "is", null);

  if (error) throw error;

  return true;
}

Deno.serve(async (req: Request) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", {
      headers: corsHeaders,
    });
  }

  try {
    const url = new URL(req.url);
    const path = url.pathname.replace(/\/+$/, "");

    if (req.method === "POST" && path.endsWith("/login")) {
      const body = await req.json();

      if (!body.username || !body.password) {
        return response(
          { error: "Usuario y contraseña son obligatorios" },
          400,
        );
      }

      try {
        const result = await login(
          body.username,
          body.password,
        );

        return response(result);
      } catch (error) {
        return response(
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

    const auth = await requireAuth(req);

    if (!auth) {
      return response(
        { error: "Sesión no válida o expirada" },
        401,
      );
    }

    if (req.method === "GET" && path.endsWith("/state")) {
      const state = await getState();

      return response({
        state,
        user: auth,
      });
    }

    if (req.method === "POST") {
      const body = await req.json();

      if (body.action === "upsert") {
        const result = await upsertRecord(
          body.table,
          body.record,
        );

        return response({
          success: true,
          data: result,
        });
      }

      if (body.action === "bulkUpsert") {
        const result = await bulkUpsert(
          body.table,
          body.records || [],
        );

        return response({
          success: true,
          data: result,
        });
      }

      if (body.action === "clear") {
        if (auth.role !== "superadmin") {
          return response(
            { error: "Se requiere Super Admin" },
            403,
          );
        }

        await clearTable(body.table);

        return response({
          success: true,
        });
      }
    }

    return response(
      { error: "Ruta o acción no válida" },
      404,
    );
  } catch (error) {
    console.error(error);

    return response(
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
