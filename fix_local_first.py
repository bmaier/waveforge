#!/usr/bin/env python3
"""
Fix: Implement local-first strategy
- Always save locally to IndexedDB
- Always load from local first
- Server only as fallback
"""

import re

# Read the file
with open('static/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the mediaRecorder.onstop handler
old_pattern = r'''if \(wasOnline && allUploaded && ConnectionMonitor\.isOnline\) \{\\n\s+// ✅ ONLINE-MODUS:.*?openSaveModal\(false\);\\n\s+\}'''

new_code = '''// 🔄 LOCAL-FIRST STRATEGIE: Immer lokal assemblieren und speichern
                    console.log('📦 Assembling recording locally (local-first strategy)...');
                    showToast('Saving recording locally...');
                    
                    // Assembliere lokal aus IndexedDB
                    await CrashGuard.assembleSession(currentSessionId, false);
                    
                    // Automatisch in IndexedDB speichern (ohne Modal)
                    if (tempBlob && tempBlob.size > 0) {
                        const autoName = currentRecordingName || `Recording_${new Date().toLocaleTimeString()}`;
                        
                        const tx = db.transaction([STORE_RECORDINGS], 'readwrite');
                        tx.objectStore(STORE_RECORDINGS).add({
                            name: autoName, 
                            blob: tempBlob, // Immer lokaler Blob!
                            date: new Date().toISOString(), 
                            mimeType: preferredMimeType, 
                            extension: preferredExt,
                            sessionId: currentSessionId,
                            isServerBacked: false, // Lokal gespeichert
                            wasOnlineDuringRecording: wasOnline, // Info für später
                            serverSynced: false // Noch nicht mit Server synchronisiert
                        });
                        
                        tx.oncomplete = () => {
                            showToast(`✓ Saved locally as .${preferredExt.toUpperCase()}`);
                            
                            // Bei Online-Aufnahme: Sende Assembly-Signal an Server (Background)
                            if (wasOnline && allUploaded && ConnectionMonitor.isOnline) {
                                console.log('🔄 Triggering server assembly in background...');
                                const fileName = `${autoName}.${preferredExt}`;
                                const metadata = {
                                    name: autoName,
                                    mimeType: preferredMimeType,
                                    extension: preferredExt,
                                    totalChunks: totalChunks,
                                    recordingCompletedAt: new Date().toISOString()
                                };
                                
                                CrashGuard.signalRecordingComplete(currentSessionId, fileName, metadata)
                                    .then(() => {
                                        console.log('✓ Server assembly completed (background)');
                                    })
                                    .catch(err => {
                                        console.warn('⚠ Server assembly failed (not critical):', err);
                                    });
                            }
                            
                            // Cleanup
                            CrashGuard.clearSession(currentSessionId);
                            tempBlob = null;
                            currentSessionId = null;
                            loadTracksFromDB();
                        };
                        
                        tx.onerror = (e) => {
                            console.error("❌ DB Save Error:", e);
                            showToast("Failed to save locally", true);
                        };
                        
                    } else {
                        console.error('❌ No audio data assembled');
                        showToast('Recording failed: No audio data', true);
                    }'''

# Replace with regex
content = re.sub(old_pattern, new_code, content, flags=re.DOTALL)

# Write back
with open('static/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed mediaRecorder.onstop handler")
