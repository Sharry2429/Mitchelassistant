package com.systemmcp.companion

import android.content.Context
import android.net.nsd.NsdManager
import android.net.nsd.NsdServiceInfo
import android.util.Log

class MitchellDiscovery(private val context: Context) {
    companion object {
        private const val SERVICE_TYPE = "_mitchell._tcp."
        private const val TAG = "MitchellDiscovery"
    }

    private val nsdManager: NsdManager = context.getSystemService(Context.NSD_SERVICE) as NsdManager
    private var discoveryListener: NsdManager.DiscoveryListener? = null
    private var resolveListener: NsdManager.ResolveListener? = null

    var onServerFound: ((String, Int) -> Unit)? = null

    fun startDiscovery() {
        Log.d(TAG, "Starting mDNS discovery for Mitchell Server")
        
        discoveryListener = object : NsdManager.DiscoveryListener {
            override fun onDiscoveryStarted(regType: String) {
                Log.d(TAG, "Service discovery started")
            }

            override fun onServiceFound(service: NsdServiceInfo) {
                Log.d(TAG, "Service found: \${service.serviceName}")
                if (service.serviceType == SERVICE_TYPE) {
                    resolveService(service)
                }
            }

            override fun onServiceLost(service: NsdServiceInfo) {
                Log.e(TAG, "Service lost: \$service")
            }

            override fun onDiscoveryStopped(serviceType: String) {
                Log.i(TAG, "Discovery stopped: \$serviceType")
            }

            override fun onStartDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Discovery failed: Error code: \$errorCode")
                nsdManager.stopServiceDiscovery(this)
            }

            override fun onStopDiscoveryFailed(serviceType: String, errorCode: Int) {
                Log.e(TAG, "Discovery failed: Error code: \$errorCode")
                nsdManager.stopServiceDiscovery(this)
            }
        }

        nsdManager.discoverServices(SERVICE_TYPE, NsdManager.PROTOCOL_DNS_SD, discoveryListener)
    }

    private fun resolveService(service: NsdServiceInfo) {
        resolveListener = object : NsdManager.ResolveListener {
            override fun onResolveFailed(serviceInfo: NsdServiceInfo, errorCode: Int) {
                Log.e(TAG, "Resolve failed: \$errorCode")
            }

            override fun onServiceResolved(serviceInfo: NsdServiceInfo) {
                Log.d(TAG, "Resolve Succeeded. \${serviceInfo.serviceName}")
                val host = serviceInfo.host.hostAddress
                val port = serviceInfo.port
                Log.d(TAG, "Resolved IP: \$host Port: \$port")
                if (host != null) {
                    onServerFound?.invoke(host, port)
                }
            }
        }
        
        try {
            nsdManager.resolveService(service, resolveListener)
        } catch (e: IllegalArgumentException) {
            Log.e(TAG, "Resolve error (likely already resolving): \${e.message}")
        }
    }

    fun stopDiscovery() {
        discoveryListener?.let {
            try {
                nsdManager.stopServiceDiscovery(it)
            } catch (e: Exception) {
                Log.e(TAG, "Error stopping discovery: \${e.message}")
            }
        }
        discoveryListener = null
        resolveListener = null
    }
}
