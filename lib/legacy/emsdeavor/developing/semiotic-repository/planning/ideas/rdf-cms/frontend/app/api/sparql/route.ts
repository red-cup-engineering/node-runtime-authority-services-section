import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { query } = await request.json();
    
    const fusekiUrl = process.env.RDF_STORAGE_URL || 'http://localhost:3000/sparql';
    
    const response = await fetch(fusekiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify({ query }),
    });
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'SPARQL query failed', details: await response.text() },
        { status: response.status }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error', details: String(error) },
      { status: 500 }
    );
  }
}
