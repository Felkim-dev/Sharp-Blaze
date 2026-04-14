#pragma once

#include <sstream>
#include <string>


#ifdef _WIN32

    #include <winsock2.h>
    #include <ws2tcpip.h>

    //#pragma comment (lib, "ws2_32.lib")

    typedef int socklen_t;

    #define NET_EWOULDBLOCK WSAEWOULDBLOCK
    
#else

    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <unistd.h>
    #include <cerrno>
    #include <fcntl.h>

    typedef int SOCKET;
    const int INVALID_SOCKET = -1;
    const int SOCKET_ERROR    = -1;

    #define NET_EWOULDBLOCK EWOULDBLOCK

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
    
    //metodos para implementar el UDP
    
    inline bool SetNonBlocking(SOCKET s)
    {
        #ifdef _WIN32
            u_long mode =1;
            return ioctlsocket(s,FIONBIO,&mode) == 0;
        #else

            int flags = fcntl(s, F_GETFL, 0);
            if (flags == -1)
            {
                return false;
            }
            return fcntl(s, F_SETFL, flags | O_NONBLOCK) == 0;
        #endif
    }
    // inline std::string GetIPString(const sockaddr_in& addr)
    // {
    //     const uint32_t ip = ntohl(addr.sin_addr.s_addr);

    //     std::ostringstream ss;
    //     ss << ((ip >> 24) & 0xFF) << '.'
    //        << ((ip >> 16) & 0xFF) << '.'
    //        << ((ip >> 8) & 0xFF) << '.'
    //        << (ip & 0xFF);

    //     return ss.str();
    // }
}