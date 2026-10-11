import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  try {
    const { update } = await request.json();
    
    const fusekiUrl = process.env.FUSEKI_URL || 'http://localhost:3030/ds/update';
    
    const response = await fetch(fusekiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: `update=${encodeURIComponent(update)}`,
    });
    
    if (!response.ok) {
      return NextResponse.json(
        { error: 'SPARQL update failed', details: await response.text() },
        { status: response.status }
      );
    }
    
    return NextResponse.json({ success: true });
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error', details: String(error) },
      { status: 500 }
    );
  }
}
