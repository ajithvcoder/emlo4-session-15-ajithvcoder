import { NextRequest, NextResponse } from "next/server";

const WEB_SERVER_URL = process.env.WEB_SERVER_URL || "http://localhost:80";

// const BACKEND_URL = "http://web-server-service"

export async function POST(request: NextRequest) {
  try {
    const formData = await request.formData();
    // const prompt = formData.get("text");
    const imageFile = formData.get("image");

    if (!(imageFile instanceof Blob)) {
      throw new Error("No valid image file provided");
    }

    const url = new URL(`${WEB_SERVER_URL}/classify-catdog`);
    console.log("web url")
    console.log(url);
    // url.searchParams.append("text", prompt as string);
    const backendFormData = new FormData();
    backendFormData.append("image", imageFile);

    const response = await fetch(url, {
      method: "POST",
      body: backendFormData,
    });

    if (!response.ok) {
      throw new Error(`Backend responded with status ${response.status}`);
    }
 
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("Error predicting image:", error);
    return NextResponse.json(
      { error: "Failed to predicting image" },
      { status: 500 }
    );
  }
} 