/*
 * lora_radio.c — SX1262 LoRa transceiver driver
 *
 * SPI0 interface (GP2-5) for SX1262 communication.
 * Sends 18-byte detection packets at SF7, 125kHz bandwidth.
 *
 * SPDX-License-Identifier: MIT
 * Copyright (c) 2026 jayis1
 */

#include "lora_radio.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"
#include "pico/stdlib.h"
#include <string.h>
#include <stdio.h>

static const char TAG[] = "LORA";

/* SX1262 SPI interface pins */
#define SPI_PORT    spi0
#define PIN_SCLK    2
#define PIN_MISO    3
#define PIN_MOSI    4
#define PIN_NSS     5
#define PIN_DIO1    6
#define PIN_RESET    7
#define PIN_BUSY    11

/* SX1262 register/command definitions */
#define SX1262_CMD_WRITE_REGISTER      0x0D
#define SX1262_CMD_READ_REGISTER       0x1D
#define SX1262_CMD_WRITE_BUFFER        0x0E
#define SX1262_CMD_READ_BUFFER         0x1E
#define SX1262_CMD_SET_TX               0x83
#define SX1262_CMD_SET_RX               0x82
#define SX1262_CMD_SET_STANDBY          0x80
#define SX1262_CMD_SET_PACKET_TYPE      0x8A
#define SX1262_CMD_SET_RF_FREQUENCY    0x86
#define SX1262_CMD_SET_TX_PARAMS       0x8E
#define SX1262_CMD_SET_MODULATION      0x89
#define SX1262_CMD_SET_PACKET_PARAMS   0x8C
#define SX1262_CMD_CLEAR_IRQ           0x02
#define SX1262_CMD_GET_IRQ_STATUS      0x12
#define SX1262_CMD_GET_STATUS          0xC0

/* Register addresses */
#define SX1262_REG_PKT_SYNC_WORD      0x0740

/* Packet type: LoRa */
#define PACKET_TYPE_LORA              0x01

/* LoRa parameters */
#define RF_FREQUENCY_868              868000000  /* 868 MHz (EU) */
#define RF_FREQUENCY_915              915000000  /* 915 MHz (US) */
#define TX_POWER_DBM                  22         /* Max power */
#define BANDWIDTH                     125000     /* 125 kHz */
#define SPREADING_FACTOR              7          /* SF7 */
#define CODING_RATE                   1          /* CR 4/5 */
#define PREAMBLE_LENGTH               8
#define SYNC_WORD                     0x3444     /* Private network */
#define TX_TIMEOUT_MS                 5000

/* Detection packet format */
#define PACKET_SYNC_BYTE              0xAA
#define PACKET_HEADER_LEN             2   /* sync + length */
#define PACKET_PAYLOAD_LEN            16  /* time(4)+lat(4)+lon(4)+class(1)+conf(1)+crc(2) */
#define PACKET_TOTAL_LEN              (PACKET_HEADER_LEN + PACKET_PAYLOAD_LEN)

static bool initialized = false;
static uint8_t tx_buffer[64];

/* Wait for SX1262 BUSY line to go low */
static void sx1262_wait_busy(void)
{
    while (gpio_get(PIN_BUSY)) {
        tight_loop_contents();
    }
}

/* SPI transaction with SX1262 */
static void sx1262_spi_write(const uint8_t *data, size_t len)
{
    gpio_put(PIN_NSS, 0);  /* CS low */
    sx1262_wait_busy();
    spi_write_blocking(SPI_PORT, data, len);
    gpio_put(PIN_NSS, 1);  /* CS high */
}

static void sx1262_spi_read(uint8_t cmd, uint8_t *data, size_t len)
{
    gpio_put(PIN_NSS, 0);
    sx1262_wait_busy();
    spi_write_blocking(SPI_PORT, &cmd, 1);
    spi_read_blocking(SPI_PORT, 0x00, data, len);
    gpio_put(PIN_NSS, 1);
}

/* Write a register on SX1262 */
static void sx1262_write_register(uint16_t addr, uint8_t value)
{
    uint8_t buf[4] = {
        SX1262_CMD_WRITE_REGISTER,
        (addr >> 8) & 0xFF,
        addr & 0xFF,
        value
    };
    sx1262_spi_write(buf, 4);
}

/* Set SX1262 to standby mode */
static void sx1262_set_standby(void)
{
    uint8_t cmd = SX1262_CMD_SET_STANDBY;
    sx1262_spi_write(&cmd, 1);
    /* Parameter: 0x00 = STDBY_RC, 0x01 = STDBY_XOSC */
    uint8_t param = 0x00;
    sx1262_spi_write(&param, 1);
}

/* Calculate CRC16-CCITT */
static uint16_t crc16_ccitt(const uint8_t *data, size_t len)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < len; i++) {
        crc ^= (uint16_t)data[i] << 8;
        for (int j = 0; j < 8; j++) {
            if (crc & 0x8000)
                crc = (crc << 1) ^ 0x1021;
            else
                crc <<= 1;
        }
    }
    return crc;
}

/*
 * Initialize SX1262 LoRa radio
 */
int lora_radio_init(void)
{
    if (initialized) return 0;

    /* Initialize SPI0 at 10MHz */
    spi_init(SPI_PORT, 10000000);

    gpio_set_function(PIN_SCLK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);

    gpio_init(PIN_NSS);
    gpio_set_dir(PIN_NSS, GPIO_OUT);
    gpio_put(PIN_NSS, 1);

    gpio_init(PIN_RESET);
    gpio_set_dir(PIN_RESET, GPIO_OUT);

    gpio_init(PIN_BUSY);
    gpio_set_dir(PIN_BUSY, GPIO_IN);

    gpio_init(PIN_DIO1);
    gpio_set_dir(PIN_DIO1, GPIO_IN);

    /* Hardware reset sequence */
    gpio_put(PIN_RESET, 0);
    sleep_ms(10);
    gpio_put(PIN_RESET, 1);
    sleep_ms(50);
    sx1262_wait_busy();

    /* Set standby mode */
    sx1262_set_standby();
    sleep_ms(10);

    /* Configure LoRa packet type */
    uint8_t pkt_cmd[2] = {SX1262_CMD_SET_PACKET_TYPE, PACKET_TYPE_LORA};
    sx1262_spi_write(pkt_cmd, 2);
    sleep_ms(10);

    /* Set RF frequency: 868 MHz (EU) */
    uint32_t freq = RF_FREQUENCY_868;
    /* Freq = (PLL freq) / 32MHz → register value = freq / 32000000 * 2^25 */
    uint32_t freq_reg = (uint32_t)((double)freq / 32000000.0 * 536870912.0);
    uint8_t freq_cmd[5] = {
        SX1262_CMD_SET_RF_FREQUENCY,
        (freq_reg >> 24) & 0xFF,
        (freq_reg >> 16) & 0xFF,
        (freq_reg >> 8) & 0xFF,
        freq_reg & 0xFF
    };
    sx1262_spi_write(freq_cmd, 5);
    sleep_ms(10);

    /* Set TX power: 22 dBm */
    uint8_t tx_cmd[4] = {
        SX1262_CMD_SET_TX_PARAMS,
        TX_POWER_DBM,
        0x02  /* RFO mode */
    };
    sx1262_spi_write(tx_cmd, 4);

    /* Set modulation params: SF7, BW125, CR4/5 */
    uint8_t mod_cmd[5] = {
        SX1262_CMD_SET_MODULATION,
        SPREADING_FACTOR,  /* SF7 */
        0x04,               /* BW 125kHz */
        CODING_RATE,        /* CR 4/5 */
        0x00                /* Low datarate optimize off */
    };
    sx1262_spi_write(mod_cmd, 5);

    /* Set sync word */
    sx1262_write_register(SX1262_REG_PKT_SYNC_WORD, (SYNC_WORD >> 8) & 0xFF);
    sx1262_write_register(SX1262_REG_PKT_SYNC_WORD + 1, SYNC_WORD & 0xFF);

    printf("[LORA] SX1262 initialized (868MHz, SF7, BW125, CR4/5, %ddBm)\r\n",
           TX_POWER_DBM);

    initialized = true;
    return 0;
}

/*
 * Send a detection packet via LoRa
 * Packet format: [0xAA][LEN][UTC(4)][LAT(4)][LON(4)][CLASS(1)][CONF(1)][CRC(2)]
 */
int lora_radio_send_detection(const detection_t *det)
{
    if (!initialized || det == NULL) return -1;

    /* Build packet */
    uint8_t payload[PACKET_PAYLOAD_LEN];
    int idx = 0;

    /* UTC timestamp (4 bytes, big-endian) */
    uint32_t ts = (uint32_t)det->timestamp;
    payload[idx++] = (ts >> 24) & 0xFF;
    payload[idx++] = (ts >> 16) & 0xFF;
    payload[idx++] = (ts >> 8) & 0xFF;
    payload[idx++] = ts & 0xFF;

    /* Latitude (int32 × 10^7, big-endian) */
    int32_t lat = (int32_t)(det->latitude * 1e7);
    payload[idx++] = (lat >> 24) & 0xFF;
    payload[idx++] = (lat >> 16) & 0xFF;
    payload[idx++] = (lat >> 8) & 0xFF;
    payload[idx++] = lat & 0xFF;

    /* Longitude (int32 × 10^7, big-endian) */
    int32_t lon = (int32_t)(det->longitude * 1e7);
    payload[idx++] = (lon >> 24) & 0xFF;
    payload[idx++] = (lon >> 16) & 0xFF;
    payload[idx++] = (lon >> 8) & 0xFF;
    payload[idx++] = lon & 0xFF;

    /* Class (1 byte) */
    payload[idx++] = (uint8_t)det->species;

    /* Confidence (1 byte, 0-100%) */
    payload[idx++] = (uint8_t)(det->confidence * 100.0f);

    /* CRC16 */
    uint16_t crc = crc16_ccitt(payload, idx);
    payload[idx++] = (crc >> 8) & 0xFF;
    payload[idx++] = crc & 0xFF;

    /* Full packet with sync and length */
    tx_buffer[0] = PACKET_SYNC_BYTE;
    tx_buffer[1] = PACKET_TOTAL_LEN;
    memcpy(&tx_buffer[2], payload, PACKET_PAYLOAD_LEN);

    /* Write to SX1262 TX buffer */
    uint8_t write_cmd[2 + PACKET_TOTAL_LEN];
    write_cmd[0] = SX1262_CMD_WRITE_BUFFER;
    write_cmd[1] = 0x00;  /* Offset 0 */
    memcpy(&write_cmd[2], tx_buffer, PACKET_TOTAL_LEN);
    sx1262_spi_write(write_cmd, 2 + PACKET_TOTAL_LEN);

    /* Set packet params */
    uint8_t pkt_cmd[10] = {
        SX1262_CMD_SET_PACKET_PARAMS,
        (PREAMBLE_LENGTH >> 8) & 0xFF,
        PREAMBLE_LENGTH & 0xFF,
        0x00,  /* Header type: explicit */
        PACKET_TOTAL_LEN & 0xFF,  /* Payload length */
        0x00,  /* CRC off */
        0x00   /* Standard IQ */
    };
    sx1262_spi_write(pkt_cmd, 7);

    /* Send TX command */
    uint8_t tx_cmd[4] = {
        SX1262_CMD_SET_TX,
        0x00, 0x00, (TX_TIMEOUT_MS >> 8) & 0xFF,
        TX_TIMEOUT_MS & 0xFF
    };
    sx1262_spi_write(tx_cmd, 4);

    printf("[LORA] TX: class=%s conf=%.0f%% lat=%.6f lon=%.6f\r\n",
           wildlife_class_name(det->species),
           det->confidence * 100,
           det->latitude,
           det->longitude);

    /* Wait for TX complete (polling DIO1 or timeout) */
    absolute_time_t timeout = make_timeout_time_ms(TX_TIMEOUT_MS);
    while (!gpio_get(PIN_DIO1)) {
        if (absolute_time_diff_us(get_absolute_time(), timeout) <= 0) {
            printf("[LORA] TX timeout\r\n");
            break;
        }
        sleep_ms(10);
    }

    /* Clear IRQ flags */
    uint8_t clear_cmd[3] = {SX1262_CMD_CLEAR_IRQ, 0x00, 0x00};
    sx1262_spi_write(clear_cmd, 3);

    /* Return to standby */
    sx1262_set_standby();

    return 0;
}

/*
 * Put LoRa radio into deep sleep (lowest power)
 */
void lora_radio_sleep(void)
{
    if (!initialized) return;
    sx1262_set_standby();
    printf("[LORA] Entering sleep mode\r\n");
}

/*
 * Wake LoRa radio from sleep
 */
void lora_radio_wake(void)
{
    if (!initialized) return;
    /* Toggle NSS to wake */
    gpio_put(PIN_NSS, 0);
    sleep_ms(1);
    gpio_put(PIN_NSS, 1);
    sleep_ms(10);
    sx1262_wait_busy();
    printf("[LORA] Woke from sleep\r\n");
}