#pragma once


#ifdef _WIN32

    #include <winsock2.h>
    #include <ws2tcpip.h>

    #pragma comment (lib, "ws2_32.lib")

    typedef int socklen_t;

#else

    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <cerrno>

    typedef int SOCKET;
    const int INVALID_SOCKET = -1;
    const int SOCKET_ERROR    = -1; 

#endif

namespace net
{
    // inicializa el subsistema de red
    inline bool Init()
    {
        #ifdef _WIN32
            WSADATA wsaData;
            return WSAStartup(MAKEWORD(2,2), &wsaData) ==0;

        #else

            return true;

        #endif
    }

    //limpia el subsistema de red
    inline void Cleanup()
    {
        #ifdef _WIN32
            WSACleanup();
        #endif
    }

    inline int CloseSocket(SOCKET s)
    {
        #ifdef _WIN32
            return closesocket(s);
        #else
            return close(s);
        #endif
    }

    inline int GetLastError()
    {
        #ifdef _WIN32
            return WSAGetLastError();
        #else
            return errno;
        #endif
    }

    inline bool IsValid(SOCKET s)
    {
        return s != INVALID_SOCKET;
    }

}