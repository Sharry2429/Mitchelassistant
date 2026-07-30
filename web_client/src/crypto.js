// crypto.js
// Handles Web Crypto API for AES-GCM

// Decodes a base64url string to Uint8Array
export function base64ToBuffer(base64) {
    let b64 = base64.replace(/-/g, '+').replace(/_/g, '/');
    while (b64.length % 4) {
        b64 += '=';
    }
    const binary = window.atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i);
    }
    return bytes;
}

export function bufferToBase64(buffer) {
    let binary = '';
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
}

// Import raw key bytes into a CryptoKey
export async function importKey(keyBase64Url) {
    const keyBytes = base64ToBuffer(keyBase64Url);
    return await window.crypto.subtle.importKey(
        "raw",
        keyBytes,
        { name: "AES-GCM", length: 256 },
        false,
        ["encrypt", "decrypt"]
    );
}

export async function encryptMessage(key, plainText) {
    const encoder = new TextEncoder();
    const data = encoder.encode(plainText);
    const nonce = window.crypto.getRandomValues(new Uint8Array(12));
    
    const cipherBuffer = await window.crypto.subtle.encrypt(
        { name: "AES-GCM", iv: nonce },
        key,
        data
    );
    
    // Combine nonce and ciphertext
    const cipherBytes = new Uint8Array(cipherBuffer);
    const combined = new Uint8Array(12 + cipherBytes.length);
    combined.set(nonce, 0);
    combined.set(cipherBytes, 12);
    
    return bufferToBase64(combined);
}

export async function decryptMessage(key, base64Ciphertext) {
    const combined = base64ToBuffer(base64Ciphertext);
    const nonce = combined.slice(0, 12);
    const cipherBytes = combined.slice(12);
    
    try {
        const plainBuffer = await window.crypto.subtle.decrypt(
            { name: "AES-GCM", iv: nonce },
            key,
            cipherBytes
        );
        const decoder = new TextDecoder();
        return decoder.decode(plainBuffer);
    } catch (e) {
        console.error("Decryption failed", e);
        return null;
    }
}
