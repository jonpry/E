/*
  Copyright 2012 The Netty Project
 *
 * The Netty Project licenses this file to you under the Apache License,
 * version 2.0 (the "License"); you may not use this file except in compliance
 * with the License. You may obtain a copy of the License at:
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations
 * under the License.
 */
package io.netty.example.echo;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.ChannelFuture;
import io.netty.channel.ChannelInitializer;
import io.netty.channel.ChannelOption;
import io.netty.channel.ChannelPipeline;
import io.netty.channel.EventLoopGroup;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.logging.LogLevel;
import io.netty.handler.logging.LoggingHandler;
import io.netty.handler.ssl.SslContext;
import io.netty.handler.ssl.SslContextBuilder;
import io.netty.handler.ssl.util.SelfSignedCertificate;

/**
 * Echoes back any received data from a client.
 */
public final class EchoServer {

    public static int func(int j) throws Exception {
        int i=100+j;
        return i;
    }

    public static void constant_int_test() throws Exception {
        int a = 127ub;
        int b = 128;
        int c = 32767;
        int d = 65535u;
        int e = 0xFFFFui;

        print_int(a);
        print_int(b);
        print_int(c);
        print_int(d);
        print_int(e);
    }

    public static void constant_float_test() throws Exception {
        float a = 0.111;
        float b = 2;
        float c = 0.222f;
        double d = 0.312d;
        float e = .1;
        float f = 1.;

        print_float(a);
        print_float(b);
        print_float(c);
        print_double(d);
        print_float(e);
        print_float(f);
    }

    public static int main() throws Exception {
        constant_int_test();
        constant_float_test();

        float r=1;
        r += 1;
        int i=0;
        long v=100l;
        boolean f=false;	
        f = f || true && true || ~false;
        i = f ? i - 2 + 3 * 2 / 2 % 3 << 1 >> 1 ^ 4 | 2 & 2 + (3 * 2) << 1 >>> 1: 0;
        i = i + 0x10;
        f = i > 100;
        f = i++ != 120;
        i += func(2);
        i -= (short)1;
        i |= 3;
        i <<= 2;
        i >>= 1;
        i >>>= 1;
        i *= 1;
        i /= 1;
        i %= 1000;
        i &= 0xFFFFF;
        i ^= 1;
        print_int(i);
        return i;
    }
}

