"use strict";

const OpenAI = require("openai");
const {zodTextFormat} = require(
    "openai/helpers/zod",
);

const {getAiConfig} = require("./ai_config");

/**
 * Creates the OpenAI SDK client.
 *
 * @return {OpenAI} OpenAI client.
 */
function createOpenAiClient() {
  const apiKey = String(
      process.env.OPENAI_API_KEY || "",
  ).trim();

  if (!apiKey) {
    throw new Error(
        "OPENAI_API_KEY is not available",
    );
  }

  return new OpenAI({
    apiKey,
  });
}

/**
 * Executes a schema-validated OpenAI Responses request.
 *
 * @param {object} options Request options.
 * @param {string} options.schemaName Schema name.
 * @param {object} options.schema Zod validation schema.
 * @param {string} options.systemPrompt System instruction.
 * @param {string} options.userPrompt User instruction.
 * @param {string=} options.model Optional model override.
 * @return {Promise<object>} Parsed structured result.
 */
async function generateStructuredResponse({
  schemaName,
  schema,
  systemPrompt,
  userPrompt,
  model,
}) {
  const config = getAiConfig();
  const client = createOpenAiClient();

  const controller = new AbortController();

  const timeout = setTimeout(
      () => controller.abort(),
      config.requestTimeoutMs,
  );

  try {
    const response = await client.responses.parse({
      model: model || config.model,
      input: [
        {
          role: "system",
          content: systemPrompt,
        },
        {
          role: "user",
          content: userPrompt,
        },
      ],
      text: {
        format: zodTextFormat(
            schema,
            schemaName,
        ),
      },
    }, {
      signal: controller.signal,
    });

    if (!response.output_parsed) {
      throw new Error(
          "AI response did not contain parsed output",
      );
    }

    return response.output_parsed;
  } finally {
    clearTimeout(timeout);
  }
}

module.exports = {
  createOpenAiClient,
  generateStructuredResponse,
};
