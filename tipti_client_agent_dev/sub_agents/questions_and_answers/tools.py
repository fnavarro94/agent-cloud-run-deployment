from google import genai
from google.genai import types

# =========================================
# Tool: Respuesta a la pregunta del usuario
# =========================================
def answer_the_question(query: str):
    """Permite responder al usuario sus preguntas respecto a TIPTI"""
    try:
        client = genai.Client(
            vertexai=True,
            project="tipti-develop-fad3",
            location="global",
        )

        si_text1 = """
            Eres un agente que responde preguntas de clientes en Tipti. Brindar respuestas precisas a las preguntas del usuario utilizando exclusivamente la información contenida en los archivos del data store conectado:
            **Estilo de comunicación**:
            Siempre usa el pronombre \"tú\" al dirigirte al cliente.
            RECUERDA NOSOTROS OFRECEMOS UN SERVICIO ASÍ QUE NO DIGAS AYUDA
            Llama al cliente por su nombre, sin títulos ni adjetivos (no uses \"señor\", \"doña\", \"estimado\", etc.).
            Mantén oraciones cortas, con máximo 16 palabras.
            Usa lenguaje claro, directo y sin tecnicismos. Si mencionas un término específico, explícalo brevemente.
            Usa un tono **empático** cuando el cliente tenga un inconveniente, y **propositivo** cuando puedas mejorar su experiencia.
            Evita palabras negativas como: \"no se puede\", \"lamentamos\", \"problema\", \"disculpas\", \"no disponible\", etc. En su lugar, ofrece soluciones de forma positiva.
            Puedes usar emojis para complementar, pero no los reemplaces por palabras. Usa siempre piel amarilla y solo si el contexto es amigable.
        """
        # Presenta tu nombre y cargo al inicio (por ejemplo: \"Hola, soy Beta, tu asiste de Tipti.\").
        model = "gemini-2.5-flash-preview-05-20"
        contents = [
            types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=query)
            ]
            )
        ]
        tools = [
            types.Tool(
            retrieval=types.Retrieval(
                vertex_rag_store=types.VertexRagStore(
                rag_resources=[
                    types.VertexRagStoreRagResource(
                    rag_corpus="projects/tipti-develop-fad3/locations/us-central1/ragCorpora/6917529027641081856"
                    )
                ],
                )
            )
            )
        ]

        generate_content_config = types.GenerateContentConfig(
            temperature = 1,
            top_p = 1,
            seed = 0,
            max_output_tokens = 65535,
            safety_settings = [types.SafetySetting(
            category="HARM_CATEGORY_HATE_SPEECH",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
            threshold="OFF"
            ),types.SafetySetting(
            category="HARM_CATEGORY_HARASSMENT",
            threshold="OFF"
            )],
            tools = tools,
            system_instruction=[types.Part.from_text(text=si_text1)],
        )

        response_text = ""
        for chunk in client.models.generate_content_stream(
            model = model,
            contents = contents,
            config = generate_content_config,
            ):
            if not chunk.candidates or not chunk.candidates[0].content or not chunk.candidates[0].content.parts:
                continue

            if chunk.candidates and chunk.candidates[0].content and chunk.candidates[0].content.parts:
                response_text += chunk.text
            # print(chunk.text, end="")

        return {
            "success": True,
            "response": response_text.strip()
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }