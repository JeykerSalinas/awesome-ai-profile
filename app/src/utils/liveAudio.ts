export const LIVE_INPUT_SAMPLE_RATE = 16_000;
export const LIVE_OUTPUT_SAMPLE_RATE = 24_000;

export function buildLiveWebSocketUrl(apiBaseUrl: string): string {
  const url = new URL(apiBaseUrl);
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.pathname = `${url.pathname.replace(/\/$/, "")}/live/ws`;
  url.search = "";
  url.hash = "";
  return url.toString();
}

export function resampleToPcm16(
  input: Float32Array<ArrayBufferLike>,
  sourceSampleRate: number,
  targetSampleRate = LIVE_INPUT_SAMPLE_RATE
): ArrayBuffer {
  const ratio = sourceSampleRate / targetSampleRate;
  const outputLength = Math.max(1, Math.floor(input.length / ratio));
  const output = new Int16Array(outputLength);

  for (let index = 0; index < outputLength; index += 1) {
    const sourceIndex = index * ratio;
    const leftIndex = Math.floor(sourceIndex);
    const rightIndex = Math.min(leftIndex + 1, input.length - 1);
    const fraction = sourceIndex - leftIndex;
    const sample =
      input[leftIndex]! * (1 - fraction) + input[rightIndex]! * fraction;
    const clamped = Math.max(-1, Math.min(1, sample));
    output[index] = clamped < 0 ? clamped * 0x8000 : clamped * 0x7fff;
  }

  return output.buffer;
}

export function pcm16ToFloat32(buffer: ArrayBuffer): Float32Array<ArrayBuffer> {
  const pcm = new Int16Array(buffer);
  const output = new Float32Array(pcm.length);
  for (let index = 0; index < pcm.length; index += 1) {
    const sample = pcm[index]!;
    output[index] = sample / (sample < 0 ? 0x8000 : 0x7fff);
  }
  return output;
}
