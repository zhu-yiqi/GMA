from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any

from gma.apps._shell import launch_webapp_with_login_extras, run_bash
from gma.apps.offline_webapps import ensure_travel_backend as _ensure_travel_backend

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


TRAVEL_LOGIN_EMAIL = "owner@example.com"
TRAVEL_LOGIN_USERNAME = "owner"
TRAVEL_LOGIN_PASSWORD = "123456"
TRAVEL_LOGIN_FIRST_NAME = "owner"
TRAVEL_LOGIN_LAST_NAME = ""
TRAVEL_PASSWORD_HASH_123456 = "$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG"


_RUNTIME = r'''
const mongoose = require('mongoose');
const crypto = require('crypto');
const PASSWORD_HASH_123456 = "$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG";

function objectId(seed) {
  return new mongoose.Types.ObjectId(crypto.createHash('sha1').update(seed).digest('hex').slice(0, 24));
}
function now() { return new Date(); }
function dateValue(value, fallback) { return value == null ? fallback : new Date(Number(value)); }
function dateOnlyMs(value) {
  if (value == null) return null;
  const d = new Date(Number(value));
  return Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate());
}
function isoDay(value) {
  const d = new Date(Number(value));
  return new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())).toISOString();
}
function randCode(prefix, seed) {
  return prefix + crypto.createHash('sha1').update(seed).digest('hex').slice(0, 10).toUpperCase();
}
function passwordValue(asset) {
  const password = asset.password || '123456';
  return password === '123456' ? PASSWORD_HASH_123456 : password;
}
function textEq(a, b) { return String(a == null ? "" : a).trim() === String(b == null ? "" : b).trim(); }
async function collection(name) { return mongoose.connection.db.collection(name); }
async function findUser(asset) {
  const users = await collection('users');
  return users.findOne({email: asset.email}) || users.findOne({username: asset.username});
}
async function ensureUser(asset) {
  const users = await collection('users');
  const accounts = await collection('accounts');
  const email = asset.email;
  const username = asset.username || email.split('@')[0];
  const current = await users.findOne({$or: [{email}, {username}]});
  const userId = current ? current._id : objectId('travel-user:' + email);
  const setDoc = {
    firstName: asset.first_name == null ? 'Asset' : asset.first_name,
    lastName: asset.last_name == null ? 'Traveler' : asset.last_name,
    email,
    username,
    phone: asset.phone || null,
    emailVerifiedAt: current?.emailVerifiedAt || now(),
    updatedAt: now(),
  };
  await users.updateOne(
    {_id: userId},
    {$set: setDoc, $setOnInsert: {
      _id: userId,
      createdAt: now(),
      emails: [],
      avatar: null,
      coverImage: '/images/static/pexels-1287145.jpg',
      customerId: null,
      profileImage: null,
    }},
    {upsert: true},
  );
  await accounts.updateOne(
    {provider: 'credentials', providerAccountId: email},
    {$set: {
      provider: 'credentials',
      providerAccountId: email,
      type: 'credentials',
      userId,
      password: passwordValue(asset),
      updatedAt: now(),
    }, $setOnInsert: {_id: objectId('travel-account:' + email), createdAt: now()}},
    {upsert: true},
  );
  return users.findOne({_id: userId});
}
async function requireUser(email) {
  const user = await (await collection('users')).findOne({email});
  if (!user) throw new Error('Travel user not found: ' + email);
  return user;
}
async function requireFlightItinerary(asset) {
  const query = {departureAirportId: asset.from_airport, arrivalAirportId: asset.to_airport};
  if (asset.flight_code) query.flightCode = asset.flight_code;
  const day = dateOnlyMs(asset.departure_date_ms);
  if (day != null) query.date = {$gte: new Date(day), $lt: new Date(day + 86400000)};
  const itinerary = await (await collection('flightitineraries')).findOne(query, {sort: {date: 1}});
  if (!itinerary) throw new Error('Travel flight itinerary not found: ' + JSON.stringify(query));
  return itinerary;
}
async function firstSegment(itinerary) {
  const id = itinerary.segmentIds && itinerary.segmentIds[0];
  if (!id) return null;
  const flightSegments = await collection('flightsegments');
  let segment = await flightSegments.findOne({_id: id});
  if (!segment && mongoose.Types.ObjectId.isValid(String(id))) {
    segment = await flightSegments.findOne({_id: objectId(String(id))});
  }
  return segment;
}
async function firstSeat(segment) {
  if (!segment || !segment.seats || !segment.seats.length) return null;
  const seatId = segment.seats[0];
  return (await collection('seats')).findOne({_id: seatId}) || {_id: seatId};
}
async function ensureFlightBooking(asset) {
  const user = await requireUser(asset.user_email);
  const itinerary = await requireFlightItinerary(asset);
  const segment = await firstSegment(itinerary);
  const passengerCount = Math.max(1, Number(asset.passenger_count || 1));
  const passengerSeed = 'travel-flight-passenger:' + asset.user_email + ':' + asset.from_airport + ':' + asset.to_airport + ':' + isoDay(asset.departure_date_ms);
  const passengerIds = Array.from({length: passengerCount}, (_, index) => objectId(passengerSeed + ':' + index));
  const bookingId = objectId('travel-flight-booking:' + asset.user_email + ':' + asset.from_airport + ':' + asset.to_airport + ':' + isoDay(asset.departure_date_ms));
  const paymentId = objectId('travel-flight-payment:' + bookingId.toString());
  const baseFirstName = asset.passenger_first_name || user.firstName || 'Asset';
  const baseLastName = asset.passenger_last_name || user.lastName || 'Traveler';
  for (const [index, passengerId] of passengerIds.entries()) {
    await (await collection('passengers')).updateOne({_id: passengerId}, {$set: {
      firstName: index === 0 ? baseFirstName : `${baseFirstName}${index + 1}`,
      lastName: baseLastName,
      passengerType: asset.passenger_type || 'adult',
      email: asset.passenger_email || asset.user_email,
      phoneNumber: {number: asset.passenger_phone || '13000000000', dialCode: asset.passenger_phone_dial_code || '+1'},
      passportNumber: index === 0 ? (asset.passport_number || 'ASSET123456') : `${asset.passport_number || 'ASSET123456'}-${index + 1}`,
      passportExpiryDate: dateValue(asset.passport_expiry_ms, new Date('2030-01-01T00:00:00Z')),
      country: asset.passenger_country || 'United States',
      dateOfBirth: dateValue(asset.passenger_birth_ms, new Date('1990-01-01T00:00:00Z')),
      gender: asset.passenger_gender || 'other',
      frequentFlyerAirline: asset.frequent_flyer_airline || null,
      frequentFlyerNumber: asset.frequent_flyer_number || null,
      seatClass: asset.seat_class || 'economy',
      isPrimary: index === 0,
      updatedAt: now(),
    }, $setOnInsert: {_id: passengerId, createdAt: now()}}, {upsert: true});
  }
  const seatIds = segment?.seats || [];
  const selectedSeats = passengerIds.map((passengerId, index) => {
    const seat = seatIds.length ? seatIds[index % seatIds.length] : null;
    return seat ? {passengerId, seatId: seat._id || seat} : null;
  }).filter(Boolean);
  const totalFare = Number(asset.total_fare || 100);
  await (await collection('flightbookings')).updateOne({_id: bookingId}, {$set: {
    pnrCode: asset.pnr_code || randCode('GMA', bookingId.toString()),
    userId: user._id,
    flightItineraryId: itinerary._id,
    segmentIds: itinerary.segmentIds || [],
    passengers: passengerIds,
    selectedSeats,
    fareBreakdown: {},
    totalFare,
    currency: asset.currency || 'USD',
    paymentStatus: asset.payment_status || 'paid',
    ticketStatus: asset.ticket_status || 'confirmed',
    paymentId,
    earnedMiles: 0,
    userTimeZone: asset.user_timezone || 'Asia/Shanghai',
    source: 'web',
    bookedAt: dateValue(asset.booked_at_ms, now()),
    updatedAt: now(),
  }, $setOnInsert: {_id: bookingId, createdAt: now(), guaranteedReservationUntil: new Date(Date.now() + 600000)}}, {upsert: true});
  await (await collection('users')).updateOne({_id: user._id}, {$addToSet: {'flights.bookings': bookingId}, $set: {updatedAt: now()}});
  await (await collection('flightpayments')).updateOne({bookingId}, {$set: {
    bookingId,
    transactionId: 'demo_asset_' + bookingId.toString(),
    stripe_paymentIntentId: 'demo_pi_' + bookingId.toString(),
    stripe_chargeId: 'demo_ch_' + bookingId.toString(),
    paymentMethod: {id: 'demo_pm', methodType: 'card', brand: 'demo', last4: '0000'},
    amount: totalFare,
    paymentDate: Math.floor(Date.now() / 1000),
    receiptUrl: 'demo://receipt/' + bookingId.toString(),
    updatedAt: now(),
  }, $setOnInsert: {_id: paymentId, createdAt: now()}}, {upsert: true});
}
async function requireHotel(asset) {
  const query = asset.hotel_slug ? {slug: asset.hotel_slug} : {name: asset.hotel_name};
  const hotel = await (await collection('hotels')).findOne(query);
  if (!hotel) throw new Error('Travel hotel not found: ' + JSON.stringify(query));
  return hotel;
}
async function ensureHotelBooking(asset) {
  const user = await requireUser(asset.user_email);
  const hotel = await requireHotel(asset);
  const roomCount = Math.max(1, Number(asset.room_count || 1));
  let hotelRooms = [];
  if (asset.room_selections && asset.room_selections.length) {
    for (const selection of asset.room_selections) {
      const query = {hotelId: hotel._id};
      if (selection.room_number) query.roomNumber = String(selection.room_number);
      if (selection.room_type) query.roomType = selection.room_type;
      if (selection.bed_options) query.bedOptions = selection.bed_options;
      const selected = await (await collection('hotelrooms')).find(query).sort({roomNumber: 1}).limit(Number(selection.count || 1)).toArray();
      if (selected.length < Number(selection.count || 1)) throw new Error('Travel hotel room selection unavailable: ' + JSON.stringify(selection));
      hotelRooms.push(...selected);
    }
  } else {
    hotelRooms = await (await collection('hotelrooms')).find({hotelId: hotel._id}).sort({roomNumber: 1}).limit(roomCount).toArray();
  }
  if (hotelRooms.length < roomCount) throw new Error('Travel hotel has only ' + hotelRooms.length + ' room(s), requested ' + roomCount + ' for ' + hotel.name);
  const rooms = hotelRooms.map((item) => item._id);
  const checkIn = dateValue(asset.check_in_ms, now());
  const checkOut = dateValue(asset.check_out_ms, new Date(checkIn.getTime() + 86400000));
  const bookingId = objectId('travel-hotel-booking:' + asset.user_email + ':' + hotel._id + ':' + checkIn.toISOString());
  const guestCount = Math.max(1, Number(asset.guest_count || (asset.guests?.length || 1)));
  const guestIds = Array.from({length: guestCount}, (_, index) => objectId('travel-hotel-guest:' + bookingId.toString() + ':' + index));
  const paymentId = objectId('travel-hotel-payment:' + bookingId.toString());
  const baseFirstName = asset.guest_first_name || user.firstName || 'Asset';
  const baseLastName = asset.guest_last_name || user.lastName || 'Traveler';
  for (const [index, guestId] of guestIds.entries()) {
    const expectedGuest = asset.guests?.[index] || {};
    await (await collection('hotelguests')).updateOne({_id: guestId}, {$set: {
      userId: user._id,
      hotelBookingId: bookingId,
      firstName: expectedGuest.first_name || (index === 0 ? baseFirstName : `${baseFirstName}${index + 1}`),
      lastName: expectedGuest.last_name || baseLastName,
      email: expectedGuest.email || asset.user_email,
      phone: expectedGuest.phone || asset.guest_phone || '+113000000000',
      guestType: expectedGuest.guest_type || asset.guest_type || 'adult',
      age: expectedGuest.age ?? asset.guest_age ?? null,
      isPrimary: index === 0,
      updatedAt: now(),
    }, $setOnInsert: {_id: guestId, createdAt: now()}}, {upsert: true});
  }
  const totalPrice = Number(asset.total_price || hotelRooms.reduce((sum, item) => sum + Number(item.price?.base || 0), 0) || 100);
  await (await collection('hotelbookings')).updateOne({_id: bookingId}, {$set: {
    userId: user._id,
    hotelId: hotel._id,
    rooms,
    checkInDate: checkIn,
    checkOutDate: checkOut,
    guests: guestIds,
    fareBreakdown: {},
    totalPrice,
    bookingStatus: asset.booking_status || 'confirmed',
    paymentStatus: asset.payment_status || 'paid',
    source: 'web',
    bookedAt: dateValue(asset.booked_at_ms, now()),
    paymentMethod: asset.payment_method || 'card',
    paymentId,
    updatedAt: now(),
  }, $setOnInsert: {_id: bookingId, createdAt: now(), guaranteedReservationUntil: new Date(Date.now() + 600000)}}, {upsert: true});
  await (await collection('users')).updateOne({_id: user._id}, {$addToSet: {'hotels.bookings': bookingId}, $set: {updatedAt: now()}});
  await (await collection('hotelpayments')).updateOne({bookingId}, {$set: {
    bookingId,
    transactionId: 'demo_hotel_asset_' + bookingId.toString(),
    stripe_paymentIntentId: 'demo_pi_' + bookingId.toString(),
    stripe_chargeId: 'demo_ch_' + bookingId.toString(),
    paymentMethod: {id: 'demo_pm', methodType: 'card', brand: 'visa', last4: '4242'},
    amount: totalPrice,
    paymentDate: Math.floor(Date.now() / 1000),
    receiptUrl: 'demo://receipt/' + bookingId.toString(),
    updatedAt: now(),
  }, $setOnInsert: {_id: paymentId, createdAt: now()}}, {upsert: true});
}
async function requireAttraction(asset) {
  const query = asset.attraction_slug ? {slug: asset.attraction_slug} : {name: asset.attraction_name};
  const attraction = await (await collection('attractions')).findOne(query);
  if (!attraction) throw new Error('Travel attraction not found: ' + JSON.stringify(query));
  return attraction;
}
async function ensureAttractionBooking(asset) {
  const user = await requireUser(asset.user_email);
  const attraction = await requireAttraction(asset);
  const visitDate = dateValue(asset.visit_date_ms, now());
  const bookingId = objectId('travel-attraction-booking:' + asset.user_email + ':' + attraction._id + ':' + visitDate.toISOString());
  const tickets = {adult: asset.adult_tickets == null ? 1 : Number(asset.adult_tickets), child: asset.child_tickets == null ? 0 : Number(asset.child_tickets)};
  const totalPrice = Number(asset.total_price == null ? Number(attraction.entryFee?.adult || 0) * tickets.adult + Number(attraction.entryFee?.child || 0) * tickets.child : asset.total_price);
  const visitors = asset.visitors && asset.visitors.length ? asset.visitors : [{firstName: user.firstName || 'Asset', lastName: user.lastName || 'Traveler', type: 'adult'}];
  await (await collection('attractionbookings')).updateOne({_id: bookingId}, {$set: {
    userId: user._id,
    attractionId: attraction._id,
    visitDate,
    tickets,
    totalPrice,
    currency: asset.currency || attraction.entryFee?.currency || 'USD',
    bookingStatus: asset.booking_status || 'confirmed',
    paymentStatus: asset.payment_status || 'paid',
    promoCode: null,
    bookedAt: dateValue(asset.booked_at_ms, now()),
    visitors,
    bookingReference: asset.booking_reference || randCode('ATR-', bookingId.toString()),
    paymentMethod: asset.payment_method || 'card',
    updatedAt: now(),
  }, $setOnInsert: {_id: bookingId, createdAt: now()}}, {upsert: true});
  await (await collection('users')).updateOne({_id: user._id}, {$addToSet: {'attractions.bookings': bookingId}, $set: {updatedAt: now()}});
}
async function flightReviewKeys(asset) {
  const itinerary = await requireFlightItinerary(asset);
  const segment = await firstSegment(itinerary);
  let airplaneModelName = segment?.airplaneId?.model || null;
  if (!airplaneModelName && segment?.airplaneId) {
    const airplane = await (await collection('airplanes')).findOne({_id: segment.airplaneId});
    airplaneModelName = airplane?.model || null;
  }
  if (!airplaneModelName) {
    const airlineId = itinerary.carrierInCharge?._id || itinerary.carrierInCharge;
    const airplane = await (await collection('airplanes')).findOne({airlineId});
    airplaneModelName = airplane?.model || null;
  }
  if (!airplaneModelName) throw new Error('Travel flight airplane model not found');
  return {
    itinerary,
    airlineId: String(itinerary.carrierInCharge?._id || itinerary.carrierInCharge),
    departureAirportId: String(itinerary.departureAirportId?._id || itinerary.departureAirportId),
    arrivalAirportId: String(itinerary.arrivalAirportId?._id || itinerary.arrivalAirportId),
    airplaneModelName,
  };
}
async function ensureFavorite(asset) {
  const user = await requireUser(asset.user_email);
  if (asset.target === 'hotel') {
    const hotel = await requireHotel(asset);
    await (await collection('users')).updateOne({_id: user._id}, {$addToSet: {'hotels.bookmarked': hotel._id}, $set: {updatedAt: now()}});
    return;
  }
  if (asset.target === 'attraction') {
    const attraction = await requireAttraction(asset);
    await (await collection('users')).updateOne({_id: user._id}, {$addToSet: {'attractions.bookmarked': attraction._id}, $set: {updatedAt: now()}});
    return;
  }
  throw new Error('Unsupported Travel favorite target: ' + asset.target);
}
async function updateAttractionReviewStats(attractionId) {
  const stats = await (await collection('attractionreviews')).aggregate([
    {$match: {attractionId}},
    {$group: {_id: null, avgRating: {$avg: '$rating'}, count: {$sum: 1}}},
  ]).toArray();
  await (await collection('attractions')).updateOne(
    {_id: attractionId},
    {$set: {
      rating: stats.length ? Math.round(stats[0].avgRating * 10) / 10 : 0,
      reviewCount: stats.length ? stats[0].count : 0,
      updatedAt: now(),
    }},
  );
}
async function ensureReview(asset) {
  let user = await requireUser(asset.user_email).catch(() => null);
  if (!user) {
    user = await ensureUser({email: asset.user_email});
  }
  const rating = Number(Number(asset.rating).toFixed(1));
  if (asset.target === 'flight') {
    const keys = await flightReviewKeys(asset);
    const filter = {
      reviewer: user._id,
      airlineId: keys.airlineId,
      departureAirportId: keys.departureAirportId,
      arrivalAirportId: keys.arrivalAirportId,
      airplaneModelName: keys.airplaneModelName,
    };
    await (await collection('flightreviews')).updateOne(filter, {$set: {
      ...filter,
      rating,
      comment: asset.comment,
      flagged: [],
      updatedAt: now(),
    }, $setOnInsert: {_id: objectId('travel-flight-review:' + user._id + ':' + keys.airlineId + ':' + keys.departureAirportId + ':' + keys.arrivalAirportId + ':' + keys.airplaneModelName), createdAt: now()}}, {upsert: true});
    return;
  }
  if (asset.target === 'hotel') {
    const hotel = await requireHotel(asset);
    const filter = {reviewer: user._id, hotelId: hotel._id, slug: hotel.slug};
    await (await collection('hotelreviews')).updateOne(filter, {$set: {
      ...filter,
      rating,
      comment: asset.comment,
      flagged: [],
      updatedAt: now(),
    }, $setOnInsert: {_id: objectId('travel-hotel-review:' + user._id + ':' + hotel._id), createdAt: now()}}, {upsert: true});
    return;
  }
  if (asset.target === 'attraction') {
    const attraction = await requireAttraction(asset);
    const booking = await (await collection('attractionbookings')).findOne({userId: user._id, attractionId: attraction._id}, {sort: {createdAt: -1}});
    const filter = {userId: user._id, attractionId: attraction._id};
    await (await collection('attractionreviews')).updateOne(filter, {$set: {
      ...filter,
      rating,
      comment: asset.comment,
      title: asset.title || null,
      visitDate: dateValue(asset.visit_date_ms, booking?.visitDate || null),
      bookingId: booking?._id || null,
      isVerified: !!asset.is_verified,
      flagged: [],
      updatedAt: now(),
    }, $setOnInsert: {_id: objectId('travel-attraction-review:' + user._id + ':' + attraction._id), createdAt: now()}}, {upsert: true});
    await updateAttractionReviewStats(attraction._id);
    return;
  }
  throw new Error('Unsupported Travel review target: ' + asset.target);
}
async function currentUser(asset) {
  const user = await findUser(asset);
  return user ? {email: user.email, username: user.username, first_name: user.firstName, last_name: user.lastName, phone: user.phone || null} : null;
}
async function currentFlightBooking(asset) {
  const user = await requireUser(asset.user_email).catch(() => null);
  const itinerary = user ? await requireFlightItinerary(asset).catch(() => null) : null;
  if (!user || !itinerary) return null;
  const booking = await (await collection('flightbookings')).findOne({userId: user._id, flightItineraryId: itinerary._id}, {sort: {createdAt: -1}});
  if (!booking) return null;
  const passenger = booking.passengers?.[0] ? await (await collection('passengers')).findOne({_id: booking.passengers[0]}) : null;
  return {user_email: user.email, from_airport: itinerary.departureAirportId, to_airport: itinerary.arrivalAirportId, flight_code: itinerary.flightCode || null, departure_date: itinerary.date ? new Date(itinerary.date).toISOString() : null, passenger_first_name: passenger?.firstName || null, passenger_last_name: passenger?.lastName || null, passenger_email: passenger?.email || null, passenger_phone: passenger?.phoneNumber?.number || null, passenger_phone_dial_code: passenger?.phoneNumber?.dialCode || null, passenger_type: passenger?.passengerType || null, passenger_count: booking.passengers?.length || 0, passenger_gender: passenger?.gender || null, passenger_country: passenger?.country || null, passenger_birth: passenger?.dateOfBirth ? new Date(passenger.dateOfBirth).toISOString() : null, passport_number: passenger?.passportNumber || null, passport_expiry: passenger?.passportExpiryDate ? new Date(passenger.passportExpiryDate).toISOString() : null, frequent_flyer_airline: passenger?.frequentFlyerAirline || null, frequent_flyer_number: passenger?.frequentFlyerNumber || null, seat_class: passenger?.seatClass || null, payment_status: booking.paymentStatus || null, ticket_status: booking.ticketStatus || null, pnr_code: booking.pnrCode || null, booked_at: booking.bookedAt ? new Date(booking.bookedAt).toISOString() : null};
}
async function currentHotelBooking(asset) {
  const user = await requireUser(asset.user_email).catch(() => null);
  const hotel = user ? await requireHotel(asset).catch(() => null) : null;
  if (!user || !hotel) return null;
  const booking = await (await collection('hotelbookings')).findOne({userId: user._id, hotelId: hotel._id}, {sort: {createdAt: -1}});
  if (!booking) return null;
  const guestDocs = booking.guests?.length ? await (await collection('hotelguests')).find({_id: {$in: booking.guests}}).toArray() : [];
  const guestsById = new Map(guestDocs.map((guest) => [String(guest._id), guest]));
  const guests = (booking.guests || []).map((id) => {
    const guest = guestsById.get(String(id));
    return guest ? {first_name: guest.firstName || null, last_name: guest.lastName || null, email: guest.email || null, phone: guest.phone || null, guest_type: guest.guestType || null, age: guest.age ?? null} : null;
  }).filter(Boolean);
  const roomDocs = booking.rooms?.length ? await (await collection('hotelrooms')).find({_id: {$in: booking.rooms}}).toArray() : [];
  const roomsById = new Map(roomDocs.map((room) => [String(room._id), room]));
  const rooms = (booking.rooms || []).map((id) => {
    const room = roomsById.get(String(id));
    return room ? {room_type: room.roomType || null, room_number: room.roomNumber || null, bed_options: room.bedOptions || null} : null;
  }).filter(Boolean);
  const guest = guests[0] || null;
  return {user_email: user.email, hotel_name: hotel.name, hotel_slug: hotel.slug, check_in: booking.checkInDate ? new Date(booking.checkInDate).toISOString() : null, check_out: booking.checkOutDate ? new Date(booking.checkOutDate).toISOString() : null, guest_first_name: guest?.first_name || null, guest_last_name: guest?.last_name || null, guests, guest_count: booking.guests?.length || 0, rooms, room_count: booking.rooms?.length || 0, booking_status: booking.bookingStatus || null, payment_status: booking.paymentStatus || null, booked_at: booking.bookedAt ? new Date(booking.bookedAt).toISOString() : null};
}
async function currentAttractionBooking(asset) {
  const user = await requireUser(asset.user_email).catch(() => null);
  const attraction = user ? await requireAttraction(asset).catch(() => null) : null;
  if (!user || !attraction) return null;
  const query = {userId: user._id, attractionId: attraction._id};
  const visitDay = dateOnlyMs(asset.visit_date_ms);
  if (visitDay != null) query.visitDate = {$gte: new Date(visitDay), $lt: new Date(visitDay + 86400000)};
  const booking = await (await collection('attractionbookings')).findOne(query, {sort: {createdAt: -1}});
  if (!booking) return null;
  return {user_email: user.email, attraction_name: attraction.name, attraction_slug: attraction.slug, visit_date: booking.visitDate ? new Date(booking.visitDate).toISOString() : null, adult_tickets: booking.tickets?.adult || 0, child_tickets: booking.tickets?.child || 0, visitors: booking.visitors || [], booking_status: booking.bookingStatus || null, payment_status: booking.paymentStatus || null, booking_reference: booking.bookingReference || null};
}
async function currentFavorite(asset) {
  const user = await requireUser(asset.user_email).catch(() => null);
  if (!user) return null;
  if (asset.target === 'hotel') {
    const hotel = await requireHotel(asset).catch(() => null);
    if (!hotel) return null;
    const found = (user.hotels?.bookmarked || []).some((id) => String(id?._id || id) === String(hotel._id));
    return found ? {user_email: user.email, target: 'hotel', hotel_name: hotel.name, hotel_slug: hotel.slug} : null;
  }
  if (asset.target === 'attraction') {
    const attraction = await requireAttraction(asset).catch(() => null);
    if (!attraction) return null;
    const found = (user.attractions?.bookmarked || []).some((id) => String(id?._id || id) === String(attraction._id));
    return found ? {user_email: user.email, target: 'attraction', attraction_name: attraction.name, attraction_slug: attraction.slug} : null;
  }
  return null;
}
async function currentReview(asset) {
  const user = await requireUser(asset.user_email).catch(() => null);
  if (!user) return null;
  if (asset.target === 'flight') {
    const keys = await flightReviewKeys(asset).catch(() => null);
    if (!keys) return null;
    const review = await (await collection('flightreviews')).findOne({
      reviewer: user._id,
      airlineId: keys.airlineId,
      departureAirportId: keys.departureAirportId,
      arrivalAirportId: keys.arrivalAirportId,
    }, {sort: {createdAt: -1}});
    return review ? {user_email: user.email, target: 'flight', rating: review.rating, comment: review.comment, from_airport: asset.from_airport, to_airport: asset.to_airport, flight_code: keys.itinerary.flightCode || null, departure_date: keys.itinerary.date ? new Date(keys.itinerary.date).toISOString() : null} : null;
  }
  if (asset.target === 'hotel') {
    const hotel = await requireHotel(asset).catch(() => null);
    if (!hotel) return null;
    const review = await (await collection('hotelreviews')).findOne({reviewer: user._id, hotelId: hotel._id, slug: hotel.slug});
    return review ? {user_email: user.email, target: 'hotel', rating: review.rating, comment: review.comment, hotel_name: hotel.name, hotel_slug: hotel.slug} : null;
  }
  if (asset.target === 'attraction') {
    const attraction = await requireAttraction(asset).catch(() => null);
    if (!attraction) return null;
    const review = await (await collection('attractionreviews')).findOne({userId: user._id, attractionId: attraction._id});
    return review ? {user_email: user.email, target: 'attraction', rating: review.rating, comment: review.comment, title: review.title || null, is_verified: !!review.isVerified, attraction_name: attraction.name, attraction_slug: attraction.slug} : null;
  }
  return null;
}
function dayMatches(actual, expectedMs) {
  if (expectedMs == null || !actual) return true;
  return dateOnlyMs(new Date(actual).getTime()) === dateOnlyMs(expectedMs);
}
function timestampMatches(actual, expectedMs) {
  if (expectedMs == null) return true;
  if (!actual) return false;
  return new Date(actual).getTime() === Number(expectedMs);
}
function normalizePhone(value) {
  if (value == null) return null;
  let digits = String(value).replace(/\D/g, '');
  if (digits.length === 11 && digits.startsWith('1')) digits = digits.slice(1);
  return digits;
}
function phoneMatches(actual, expected) {
  if (expected == null) return true;
  return normalizePhone(actual) === normalizePhone(expected);
}
async function probe(asset) {
  let current = null;
  let exact = false;
  if (asset.kind === 'travel_user') {
    current = await currentUser(asset);
    exact = !!current && current.email === asset.email && current.username === (asset.username || asset.email.split('@')[0]) && current.first_name === (asset.first_name == null ? 'Asset' : asset.first_name) && current.last_name === (asset.last_name == null ? 'Traveler' : asset.last_name);
  } else if (asset.kind === 'travel_flight_booking') {
    current = await currentFlightBooking(asset);
    exact = !!current && current.user_email === asset.user_email && current.from_airport === asset.from_airport && current.to_airport === asset.to_airport && (asset.flight_code == null || current.flight_code === asset.flight_code) && dayMatches(current.departure_date, asset.departure_date_ms) && (asset.passenger_first_name == null || current.passenger_first_name === asset.passenger_first_name) && (asset.passenger_last_name == null || current.passenger_last_name === asset.passenger_last_name) && (asset.passenger_email == null || current.passenger_email === asset.passenger_email) && (asset.passenger_phone == null || current.passenger_phone === asset.passenger_phone) && (asset.passenger_phone_dial_code == null || current.passenger_phone_dial_code === asset.passenger_phone_dial_code) && current.passenger_type === (asset.passenger_type || 'adult') && (asset.passenger_count == null || current.passenger_count === Number(asset.passenger_count)) && current.passenger_gender === (asset.passenger_gender || 'other') && current.passenger_country === (asset.passenger_country || 'United States') && (asset.passenger_birth_ms == null || dayMatches(current.passenger_birth, asset.passenger_birth_ms)) && (asset.passport_number == null || current.passport_number === asset.passport_number) && (asset.passport_expiry_ms == null || dayMatches(current.passport_expiry, asset.passport_expiry_ms)) && (asset.frequent_flyer_airline == null || current.frequent_flyer_airline === asset.frequent_flyer_airline) && (asset.frequent_flyer_number == null || current.frequent_flyer_number === asset.frequent_flyer_number) && current.seat_class === (asset.seat_class || 'economy') && current.payment_status === (asset.payment_status || 'paid') && current.ticket_status === (asset.ticket_status || 'confirmed') && timestampMatches(current.booked_at, asset.booked_at_ms);
  } else if (asset.kind === 'travel_hotel_booking') {
    current = await currentHotelBooking(asset);
    const expectedGuests = asset.guests || [];
    const currentGuests = current?.guests || [];
    const guestsMatch = expectedGuests.length === 0 || (currentGuests.length === expectedGuests.length && expectedGuests.every((guest, index) => currentGuests[index]?.first_name === guest.first_name && currentGuests[index]?.last_name === guest.last_name && (guest.email == null || currentGuests[index]?.email === guest.email) && phoneMatches(currentGuests[index]?.phone, guest.phone) && currentGuests[index]?.guest_type === (guest.guest_type || 'adult') && (guest.age == null || currentGuests[index]?.age === guest.age)));
    const expectedRoomSelections = asset.room_selections || [];
    const currentRooms = current?.rooms || [];
    const roomSelectionsMatch = expectedRoomSelections.length === 0 || expectedRoomSelections.every((selection) => {
      const count = Number(selection.count || 1);
      return currentRooms.filter((room) => (selection.room_type == null || room.room_type === selection.room_type) && (selection.room_number == null || String(room.room_number) === String(selection.room_number)) && (selection.bed_options == null || room.bed_options === selection.bed_options)).length === count;
    });
    exact = !!current && current.user_email === asset.user_email && (asset.hotel_slug ? current.hotel_slug === asset.hotel_slug : current.hotel_name === asset.hotel_name) && dayMatches(current.check_in, asset.check_in_ms) && dayMatches(current.check_out, asset.check_out_ms) && (asset.guest_first_name == null || current.guest_first_name === asset.guest_first_name) && (asset.guest_last_name == null || current.guest_last_name === asset.guest_last_name) && (asset.guest_count == null || current.guest_count === Number(asset.guest_count)) && (asset.room_count == null || current.room_count === Number(asset.room_count)) && guestsMatch && roomSelectionsMatch && current.booking_status === (asset.booking_status || 'confirmed') && current.payment_status === (asset.payment_status || 'paid') && timestampMatches(current.booked_at, asset.booked_at_ms);
  } else if (asset.kind === 'travel_attraction_booking') {
    current = await currentAttractionBooking(asset);
    const expectedVisitors = asset.visitors || [];
    const currentVisitors = current?.visitors || [];
    const visitorsMatch = expectedVisitors.length === 0 || (currentVisitors.length === expectedVisitors.length && expectedVisitors.every((visitor, index) => currentVisitors[index]?.firstName === visitor.firstName && currentVisitors[index]?.lastName === visitor.lastName && currentVisitors[index]?.type === (visitor.type || 'adult')));
    exact = !!current && current.user_email === asset.user_email && (asset.attraction_slug == null || current.attraction_slug === asset.attraction_slug) && (asset.attraction_name == null || current.attraction_name === asset.attraction_name) && dayMatches(current.visit_date, asset.visit_date_ms) && current.adult_tickets === (asset.adult_tickets == null ? 1 : asset.adult_tickets) && current.child_tickets === (asset.child_tickets == null ? 0 : asset.child_tickets) && visitorsMatch && current.booking_status === (asset.booking_status || 'confirmed') && current.payment_status === (asset.payment_status || 'paid');
  } else if (asset.kind === 'travel_favorite') {
    current = await currentFavorite(asset);
    exact = !!current && current.user_email === asset.user_email && current.target === asset.target;
  } else if (asset.kind === 'travel_review') {
    current = await currentReview(asset);
    exact = !!current && current.user_email === asset.user_email && current.target === asset.target && (asset.target !== 'attraction' || asset.attraction_slug == null || current.attraction_slug === asset.attraction_slug) && (asset.target !== 'attraction' || asset.attraction_name == null || current.attraction_name === asset.attraction_name) && Number(current.rating) === Number(asset.rating) && textEq(current.comment, asset.comment) && (asset.target !== 'attraction' || asset.title == null || textEq(current.title, asset.title)) && (asset.target !== 'attraction' || asset.is_verified == null || current.is_verified === !!asset.is_verified);
  } else {
    throw new Error('Unsupported Travel asset kind: ' + asset.kind);
  }
  return {label: asset.kind + ':' + (asset.email || asset.user_email || ''), identity_exists: !!current, exact_match: exact, current};
}
async function apply(asset) {
  if (asset.kind === 'travel_user') return ensureUser(asset);
  if (asset.kind === 'travel_flight_booking') return ensureFlightBooking(asset);
  if (asset.kind === 'travel_hotel_booking') return ensureHotelBooking(asset);
  if (asset.kind === 'travel_attraction_booking') return ensureAttractionBooking(asset);
  if (asset.kind === 'travel_favorite') return ensureFavorite(asset);
  if (asset.kind === 'travel_review') return ensureReview(asset);
  throw new Error('Unsupported Travel asset kind: ' + asset.kind);
}
'''


def _run_travel_runtime(client: AndroidController, asset: Any, mode: str) -> dict[str, Any] | None:
    _ensure_travel_backend(client)
    if hasattr(asset, "model_dump"):
        asset_payload = asset.model_dump(mode="json")
    else:
        asset_payload = asset
    payload = base64.b64encode(json.dumps(asset_payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    runtime_b64 = base64.b64encode(_RUNTIME.encode("utf-8")).decode("ascii")
    command = f"""
set -euo pipefail
RUNTIME_B64={runtime_b64!r}
ASSET_B64={payload!r}
MODE={mode!r}
docker exec -e RUNTIME_B64="$RUNTIME_B64" -e ASSET_B64="$ASSET_B64" -e MODE="$MODE" -i travel-app node - <<'NODE'
const runtime = Buffer.from(process.env.RUNTIME_B64, 'base64').toString('utf8');
const asset = JSON.parse(Buffer.from(process.env.ASSET_B64, 'base64').toString('utf8'));
const mode = process.env.MODE;
const mongoose = require('mongoose');
(async () => {{
  eval(runtime);
  await mongoose.connect(process.env.MONGODB_URI, {{serverSelectionTimeoutMS: 5000}});
  let result = null;
  if (mode === 'probe') result = await probe(asset);
  else {{ await apply(asset); result = {{ok: true}}; }}
  console.log(JSON.stringify(result));
  await mongoose.disconnect();
}})().catch(async (error) => {{
  try {{ await mongoose.disconnect(); }} catch (e) {{}}
  console.error(error && error.stack ? error.stack : String(error));
  process.exit(1);
}});
NODE
"""
    output = run_bash(client, command, timeout=180).strip()
    return json.loads(output) if output else None


def ensure_travel_login_user(
    client: AndroidController,
    *,
    email: str = TRAVEL_LOGIN_EMAIL,
    username: str = TRAVEL_LOGIN_USERNAME,
    password: str = TRAVEL_LOGIN_PASSWORD,
    first_name: str = TRAVEL_LOGIN_FIRST_NAME,
    last_name: str = TRAVEL_LOGIN_LAST_NAME,
) -> None:
    _run_travel_runtime(
        client,
        {
            "kind": "travel_user",
            "email": email,
            "username": username,
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
        },
        "apply",
    )


def login_travel_app(
    client: AndroidController,
    *,
    email: str = TRAVEL_LOGIN_EMAIL,
    username: str | None = TRAVEL_LOGIN_USERNAME,
    password: str = TRAVEL_LOGIN_PASSWORD,
    first_name: str = TRAVEL_LOGIN_FIRST_NAME,
    last_name: str = TRAVEL_LOGIN_LAST_NAME,
    ensure_user: bool = True,
) -> None:
    if ensure_user:
        ensure_travel_login_user(
            client,
            email=email,
            username=username or email.split("@", 1)[0],
            password=password,
            first_name=first_name,
            last_name=last_name,
        )
    launch_webapp_with_login_extras(
        client,
        "gma.webapp.travel",
        username=email,
        password=password,
    )


def _travel_asset_login_details(asset: Any) -> tuple[str | None, str | None]:
    if hasattr(asset, "model_dump"):
        data = asset.model_dump(mode="json")
    elif isinstance(asset, dict):
        data = asset
    else:
        data = {}
    if data.get("kind") == "travel_review":
        return None, None
    email = data.get("email") or data.get("user_email")
    password = data.get("password") or TRAVEL_LOGIN_PASSWORD
    return email, password


def _clear_travel_server_cache(client: AndroidController) -> None:
    run_bash(
        client,
        """
set -euo pipefail
docker exec travel-app sh -lc 'rm -rf /app/.next/cache/fetch-cache 2>/dev/null || true'
""",
        timeout=30,
    )


def _travel_asset_kind(asset: Any) -> str | None:
    if hasattr(asset, "model_dump"):
        data = asset.model_dump(mode="json")
    elif isinstance(asset, dict):
        data = asset
    else:
        data = {}
    return data.get("kind")


def _clear_travel_webview_state(client: AndroidController) -> None:
    client.shell("am force-stop gma.webapp.travel >/dev/null 2>&1 || true")
    client.shell("pm clear gma.webapp.travel >/dev/null 2>&1 || true")


def apply_travel_asset(client: AndroidController, asset: Any) -> None:
    _run_travel_runtime(client, asset, "apply")
    _clear_travel_server_cache(client)
    kind = _travel_asset_kind(asset)
    email, password = _travel_asset_login_details(asset)
    if email and kind != "travel_user":
        # A user asset alone can open the WebView before later booking assets exist.
        # Clear and reopen only after data-bearing assets so client route caches do
        # not preserve an empty bookings page across task initialization.
        _clear_travel_webview_state(client)
        login_travel_app(client, email=email, password=password, ensure_user=False)


def probe_travel_asset(client: AndroidController, asset: Any) -> dict[str, Any]:
    result = _run_travel_runtime(client, asset, "probe")
    if not isinstance(result, dict):
        raise RuntimeError("Travel asset probe did not return a JSON object")
    return result
