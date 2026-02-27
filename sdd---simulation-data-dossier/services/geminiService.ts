
import { GoogleGenAI } from "@google/genai";

// Standard implementation for Gemini API interaction
export const getGeminiResponse = async (prompt: string, context: any) => {
  // Directly use process.env.API_KEY to initialize client as per guidelines
  const ai = new GoogleGenAI({ apiKey: process.env.API_KEY });

  try {
    const response = await ai.models.generateContent({
      // Using gemini-3-pro-preview for complex engineering reasoning tasks
      model: 'gemini-3-pro-preview',
      contents: `Context: You are an expert Engineering Simulation assistant for the Simulation Data Dossier (SDD) platform. 
      The current system manages heavy-duty induction motors for sugar processing plants. 
      Standards: MOSSEC, IEC 6034.
      Active Data: ${JSON.stringify(context)}
      
      User Query: ${prompt}`,
      config: {
        systemInstruction: "Provide concise, technical, and professional answers regarding simulation results, dossier status, and compliance requirements. Always refer to MOSSEC and IEC 6034 standards when relevant."
      }
    });

    // Access .text property directly (not a method) as specified in guidelines
    return response.text || "I'm sorry, I couldn't generate a response.";
  } catch (error) {
    console.error("Gemini Error:", error);
    return "An error occurred while connecting to the simulation intelligence service.";
  }
};
