FROM debian:bookworm-slim AS builder

RUN apt-get update \
	&& apt-get install -y --no-install-recommends \
		build-essential \
		cmake \
	&& rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Build context should be src/server
COPY . .

RUN cmake -S Makefile -B build/linux -DCMAKE_BUILD_TYPE=Release \
	&& cmake --build build/linux -j


FROM debian:bookworm-slim AS runtime

WORKDIR /app

COPY --from=builder /app/build/linux/sharp_blaze_server /app/sharp_blaze_server

EXPOSE 5555/tcp
EXPOSE 5556/udp

CMD ["/app/sharp_blaze_server"]
