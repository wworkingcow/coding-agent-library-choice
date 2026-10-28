#!/usr/bin/env node
// Заглушка MCP-сервера вендора: один инструмент, отдаёт официальные доки.
// usage: node mcp-stub.mjs <vendor> <path-to-DOC.md>
import { readFileSync } from "node:fs";
import { createInterface } from "node:readline";

const [vendor, docPath] = process.argv.slice(2);
const doc = readFileSync(docPath, "utf8");
const Vendor = vendor[0].toUpperCase() + vendor.slice(1);
const tool = {
  name: `${vendor}_docs`,
  description: `Official ${Vendor} documentation: how to add ${Vendor} authentication (sign up, sign in, social login, protected routes) to a Next.js app.`,
  inputSchema: { type: "object", properties: { query: { type: "string" } } },
};

const send = (msg) => process.stdout.write(JSON.stringify(msg) + "\n");

createInterface({ input: process.stdin }).on("line", (line) => {
  let req;
  try { req = JSON.parse(line); } catch { return; }
  if (req.id === undefined) return; // notification
  const ok = (result) => send({ jsonrpc: "2.0", id: req.id, result });
  if (req.method === "initialize")
    ok({ protocolVersion: "2024-11-05", capabilities: { tools: {} },
         serverInfo: { name: vendor, version: "1.0.0" } });
  else if (req.method === "tools/list") ok({ tools: [tool] });
  else if (req.method === "tools/call") ok({ content: [{ type: "text", text: doc }] });
  else send({ jsonrpc: "2.0", id: req.id, error: { code: -32601, message: "not implemented" } });
});
